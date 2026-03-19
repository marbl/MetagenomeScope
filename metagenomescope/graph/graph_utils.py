from collections import Counter
from .. import ui_utils, name_utils, config
from metagenomescope.errors import WeirdError, GraphParsingError


def get_only_connecting_edge_uid(g, src_id, tgt_id):
    """Gets the "uid" attribute of the only edge between two nodes.

    Raises an error if there is not exactly one edge between these two nodes.

    Parameters
    ----------
    g: nx.MultiDiGraph
    src_id: int
    tgt_id: int
    """
    adj = g.adj[src_id]
    suffix = f"from node ID {src_id} to node ID {tgt_id}"
    if tgt_id not in adj:
        raise WeirdError(f"0 edges {suffix}")
    if len(adj[tgt_id]) > 1:
        raise WeirdError(f"> 1 edge {suffix}")
    return g.edges[src_id, tgt_id, 0]["uid"]


def get_counterpart_parent_id(node_id, nodeid2obj):
    """Returns the ID of the parent pattern of a split node's counterpart."""
    if node_id in nodeid2obj:
        node = nodeid2obj[node_id]
        if node.is_split():
            # if it is a split node then it must be a real node, not a
            # collapsed pattern
            cid = node.counterpart_node_id
            return nodeid2obj[cid].parent_id
        else:
            raise WeirdError(f"{node} is not split?")
    else:
        raise WeirdError(f"ID {node_id} not in nodeid2obj. Is it a pattern?")


def is_split_node(node_id, nodeid2obj):
    """Returns True if a node ID corresponds to a Node that is split."""
    return node_id in nodeid2obj and nodeid2obj[node_id].is_split()


def has_onenode_split_boundaries(vr, nodeid2obj):
    """Returns True if both boundaries of a pattern are single split nodes."""
    if len(vr.start_node_ids) == 1 and len(vr.end_node_ids) == 1:
        si = vr.start_node_ids[0]
        ei = vr.end_node_ids[0]
        return is_split_node(si, nodeid2obj) and is_split_node(ei, nodeid2obj)
    return False


def counterparts_in_same_2node_chain(vr, nodeid2obj, pattid2obj):
    """Checks if the counterparts of pattern boundaries are in a 2-node chain.

    Parameters
    ----------
    vr: ValidationResults

    nodeid2obj: dict of int -> Node

    pattid2obj: dict of int -> Pattern

    Returns
    -------
    bool
        True if all of the following criteria are met:
            - vr has only a single start node S, which is a split node
            - vr has only a single end node E, which is a split node
            - The counterpart node of S, and the counterpart node of E, are
              children of the same pattern P
            - P is a chain containing just two nodes (which are the
              counterparts of S and E)

        False otherwise.

    Notes
    -----
    - This wards off jank situations like isolated cyclic bubbles: see
      https://github.com/marbl/MetagenomeScope/issues/241. In such cases,
      this check prevents the bizarre situation where you end up with a cyclic
      chain containing nothing else but a bubble.

    - This check is also very specific -- for example, if the chain P has more
      than two nodes, then this check does not return True. This is because in
      such cases, the cyclic chain you end up with (containing the pattern
      described by vr as well as the stuff already in the chain P) will at
      least contain SOMETHING besides the vr pattern. See
      test_chain_into_cyclic_chain_merging() in the hierarchical decomp. tests
      for an example of this.
    """
    if has_onenode_split_boundaries(vr, nodeid2obj):
        scpid = get_counterpart_parent_id(vr.start_node_ids[0], nodeid2obj)
        ecpid = get_counterpart_parent_id(vr.end_node_ids[0], nodeid2obj)
        # I don't THINK the parent ID of the counterpart should ever be None at
        # this point in the algorithm, but let's be careful...
        if scpid is not None and scpid == ecpid:
            p = pattid2obj[scpid]
            return p.pattern_type == config.PT_CHAIN and len(p.nodes) == 2
    return False


def check_not_splitting_a_loop(nid0, nid1, nodeid2obj):
    """Raises an error if we are trying to split a node with a loop edge.

    Parameters
    ----------
    nid0: int
    nid1: int
        These represent the two endpoints of an edge adjacent to a node that
        we are trying to split. If they are the same, then we're trying to
        split a node with at least one loop edge! Oh no! Don't do that.

    nodeid2obj: dict of int -> Node

    Notes
    -----
    In theory supporting this is totally possible, but it should never happen
    (given the sort of patterns we currently identify) and supporting this
    would introduce some truly hideous complexity, I think. Best to just
    proactively catch these cases and add support later if absolutely needed.
    """
    if nid0 == nid1:
        raise WeirdError(
            f"Trying to split {nodeid2obj[nid0]}, which has at least one "
            "edge pointing to itself? This should never happen."
        )


def get_split_halves(basename, nodename2obj):
    # If either XYZ-L or XYZ-R is not in the graph, these lines will throw a
    # KeyError, which is well and good. better to crash and burn than to show a
    # subtly incorrect graph. let our python interpreter be the first to cast
    # it into the fire or something idk
    left = nodename2obj[basename + config.SPLIT_LEFT_SUFFIX]
    right = nodename2obj[basename + config.SPLIT_RIGHT_SUFFIX]
    return left, right


def check_and_get_fake_edge_id(g, left, right, edgeid2obj):
    # There should be a single fake edge XYZ-L ==> XYZ-R
    fe_id = get_only_connecting_edge_uid(g, left.unique_id, right.unique_id)
    if not edgeid2obj[fe_id].is_fake:
        raise WeirdError(
            f'Edge ID "{fe_id}" connects {left} and {right} but is not fake?'
        )
    return fe_id


def check_node_split_properly(g, basename, nodename2obj, edgeid2obj):
    left, right = get_split_halves(basename, nodename2obj)
    return left, right, check_and_get_fake_edge_id(g, left, right, edgeid2obj)


def get_one_side_of_edge_ids(g, node_id, in_edges=True):
    eids = set()
    if in_edges:
        f = g.in_edges
    else:
        f = g.out_edges
    for _, _, data in f(node_id, data=True):
        eid = data["uid"]
        if eid in eids:
            raise WeirdError(f'Edge ID "{eid}" occurs twice?')
        eids.add(eid)
    return eids


def check_surrounding_edge_ids_unchanged(g0, g1, nid0, nid1):
    # Note that if this node has edge(s) to itself then they will be classified
    # as both in- and out-edges. This is fine!
    i0 = get_one_side_of_edge_ids(g0, nid0, in_edges=True)
    i1 = get_one_side_of_edge_ids(g1, nid1, in_edges=True)
    if i0 != i1:
        raise WeirdError(f"In-edge IDs changed from {i0} to {i1}")
    o0 = get_one_side_of_edge_ids(g0, nid0, in_edges=False)
    o1 = get_one_side_of_edge_ids(g1, nid1, in_edges=False)
    if o0 != o1:
        raise WeirdError(f"Out-edge IDs changed from {o0} to {o1}")


def check_surrounding_edge_ids_of_split(
    g0, g1, basename, original_node_id, nodename2obj, edgeid2obj
):
    # check that merging the in edges and out edges of the L and R
    # nodes matches the original edges incident on the original
    # unsplit node (noting that due to cyclic pattern jank there
    # may be out-edges on the L node and in-edges on the R node)
    left, right, fe_id = check_node_split_properly(
        g1, basename, nodename2obj, edgeid2obj
    )

    # left (in and out)
    li = get_one_side_of_edge_ids(g1, left.unique_id, in_edges=True)
    lo = get_one_side_of_edge_ids(g1, left.unique_id, in_edges=False)
    # right (in and out)
    ri = get_one_side_of_edge_ids(g1, right.unique_id, in_edges=True)
    ro = get_one_side_of_edge_ids(g1, right.unique_id, in_edges=False)

    if li & ri:
        raise WeirdError(f"Overlapping in-edges: {left}, {right}, {li}, {ri}")
    if lo & ro:
        raise WeirdError(f"Overlapping out-edges: {left}, {right}, {lo}, {ro}")

    # super paranoid, check_node_split_properly() should already
    # have verified this. so this should ESPECIALLY never happen
    if fe_id not in lo or fe_id not in ri:
        raise WeirdError(f"Fake edge doesn't connect {left} and {right}?")

    if fe_id in li or fe_id in ro:
        # this DEFINITELY won't happen, call a priest if it does
        raise WeirdError(f"Fake edge is in on {left} and/or out on {right}???")

    lo.remove(fe_id)
    ri.remove(fe_id)

    # original node (in and out)
    oi = get_one_side_of_edge_ids(g0, original_node_id, in_edges=True)
    oo = get_one_side_of_edge_ids(g0, original_node_id, in_edges=False)

    new_in = li | ri
    new_out = lo | ro

    # error messages could def be made more informative...
    if oi | oo != new_in | new_out:
        raise WeirdError(f"Inconsistent edge IDs for {basename}")
    # i guess these address the insane case where like,
    # oi | oo == new_in | new_out (i.e. the surrounding edge IDs are identical)
    # but which is in and which is out gets swapped. should never happen.
    if oi != new_in:
        raise WeirdError(f"Inconsistent in edge IDs for {basename}")
    if oo != new_out:
        raise WeirdError(f"Inconsistent out edge IDs for {basename}")


def check_surrounding_node_basenames_unchanged(
    eobj, nodeid2obj, deletednodeid2counterpartid, orig_src_id, orig_tgt_id
):
    # Account for how the original nodes might have been split, deemed
    # unnecessarily, and then replaced by their counterpart. This is super lazy
    # I'm so sorry :(((((
    if orig_src_id not in nodeid2obj:
        orig_src_id = deletednodeid2counterpartid[orig_src_id]
    if orig_tgt_id not in nodeid2obj:
        orig_tgt_id = deletednodeid2counterpartid[orig_tgt_id]
    orig_src_obj = nodeid2obj[orig_src_id]
    orig_tgt_obj = nodeid2obj[orig_tgt_id]
    new_src_obj = nodeid2obj[eobj.new_src_id]
    new_tgt_obj = nodeid2obj[eobj.new_tgt_id]
    # should still connect nodes with these basenames. Maybe one or
    # both of these nodes is split, but they should still be connected
    if orig_src_obj.basename != new_src_obj.basename:
        raise WeirdError(
            f'Edge "{eobj}" no longer originates from a node with '
            f'basename "{orig_src_obj.basename}"?'
        )
    if orig_tgt_obj.basename != new_tgt_obj.basename:
        raise WeirdError(
            f'Edge "{eobj}" no longer points to a node with '
            f'basename "{orig_tgt_obj.basename}"?'
        )


def validate_nonempty(ag):
    """Raises an error if an AssemblyGraph has 0 nodes and/or edges.

    We allow node-centric graphs to have 0 edges (so long as they have at
    least one node), but edge-centric graphs must have at least one edge
    (implying at least one node).
    """
    if ag.node_centric:
        if ag.node_ct == 0:
            raise GraphParsingError("Graph has 0 nodes.")
    else:
        # NOTE: the DOT parsing function already checks for this, so it
        # is impossible (well, not really, it's just a pain) to test these
        # branches of this function. I am leaving them in as failsafes.
        if ag.edge_ct == 0:
            raise GraphParsingError("Graph has 0 edges.")
        if ag.node_ct == 0:
            # if we make it here, the graph has >= 1 edge but 0 nodes.
            # um. that's not a graph any more i think
            raise WeirdError("Get thee behind me, satan")


def validate_multiple_ccs(ag):
    """Raises an error if an AssemblyGraph contains <= 1 components.

    Of course it is okay for a graph to have only 1 component, but this
    function is intended to be called after we have already observed that
    it contains multiple components -- it's just a sanity check.
    """
    if len(ag.components) == 1:
        raise WeirdError("Graph has only a single component")
    elif len(ag.components) < 1:
        raise WeirdError("Graph has < 1 components? Something is busted.")


def get_treemap_rectangles(cc_nums, node_ct, aggregate=True):
    """Formats components of a given node size to be represented in a treemap.

    Parameters
    ----------
    cc_nums: list of int
        List of component size ranks that all contain a given number of nodes.
        Because of the way component size ranks are produced (by sorting
        components based first on how many nodes they contain), this should
        be a continuous range. It is okay if this list contains only a single
        component size rank; this indicates that just one component contains
        node_ct nodes.

    node_ct: int
        The number of nodes that each component in cc_nums contains.

    aggregate: bool
        If True, we will only create a single rectangle (representing all of
        these components). Otherwise, we will create one rectangle for each
        component.

    Returns
    -------
    names, sizes: list of str, list of int
        "names" describes the name of each rectangle. If len(cc_nums) > 1 and
        aggregate=True, then this will be formatted in a fancy way to indicate
        that this rectangle represents multiple components.

        "sizes" describes the size of each rectangle, in terms of nodes.

        Note that, if aggregate=True, then len(names) == len(sizes) == 1.
        (Either this is because multiple components will be aggregated
        together -- if len(cc_nums) > 1 -- or it is because len(cc_nums) == 1.)

    Raises
    ------
    WeirdError
        If len(cc_nums) < 1.
        If aggregate=True and cc_nums does not represent a continuous range
        of integers.
    """
    if len(cc_nums) < 1:
        raise WeirdError("cc_nums cannot be empty")
    names = []
    sizes = []
    if len(cc_nums) > 1 and aggregate:
        min_cc_num = min(cc_nums)
        max_cc_num = max(cc_nums)
        # NOTE: now that we delegate computing the hover text template to
        # ui_utils.fmt_num_ranges(), this is no longer a strict requirement;
        # that function can describe discontinuous cc size ranks. However, we
        # should not see this happen in practice here, so let's be paranoid.
        if max_cc_num - min_cc_num + 1 != len(cc_nums):
            raise WeirdError(
                "Discontinuous size ranks: "
                f"|{min_cc_num:,} to {max_cc_num:,}| != {len(cc_nums):,}"
            )
        names.append(
            f"{ui_utils.fmt_num_ranges(cc_nums)} ({node_ct:,}-node components)"
        )
        # If we have let's say 5 components that each contain
        # exactly 3 nodes, then they represent 15 nodes total.
        sizes.append(node_ct * len(cc_nums))
    else:
        for cc_num in sorted(cc_nums):
            names.append(f"#{cc_num:,}")
            sizes.append(node_ct)
    return names, sizes


def validate_split_type(split):
    if split not in (config.SPLIT_LEFT, config.SPLIT_RIGHT, None):
        raise WeirdError(f"Invalid split type: {split}")


def get_sorted_subgraphs(sgs):
    # The number of "full" nodes (i.e. ignoring node splitting) MUST be the
    # highest-priority sorting criterion. Otherwise, we will be unable to
    # say that an aggregated group of components with the exact same
    # amount of nodes represents a continuous range of component size
    # ranks. See the treemap plot code.
    return sorted(
        sgs,
        key=lambda obj: (
            obj.num_full_nodes,
            obj.num_total_nodes,
            obj.num_total_edges,
            obj.pattern_stats.sum(),
        ),
        reverse=True,
    )


def get_candidate_twin_cc_num_from_nodes(cc, nodename2objs):
    """Looks at the nodes in a Component to determine a possible twin.

    This is not guaranteed to actually be a twin Component! This is
    just "phase 1" of a redundant Component detection process. You
    still need to compare the total node / edge counts between the
    components, as well as the edges.

    Parameters
    ----------
    cc: Component

    nodename2objs: dict of str -> list of Node

    Returns
    -------
    int or None
    """
    if len(cc.nodes) == 0:
        raise WeirdError(f"0-node cc {cc}; should never happen :(")

    candidate_twin_cc_num = None

    for n in cc.nodes:
        # If a node is split into X-L ==> X-R, only consider X-L
        # (the choice is arbitrary). This is only for performance;
        # it should be safe to comment this out (in which case we
        # will just be overcautious and check both splits of X)
        if n.is_split() and n.split == config.SPLIT_RIGHT:
            continue

        # Negate the BASENAME -- if we are looking at X-L, don't look up -X-L,
        # since -X may or may not have been split. Just look up -X. (Like,
        # decomposition should USUALLY be symmetric, but this is not guaranteed
        # yet so let's be safe.)
        rc_name = name_utils.negate(n.basename)
        if rc_name in nodename2objs:
            # Using [0] here means that -- if -X is split -- then we will
            # just pick one of {-X-L, -X-R} arbitrarily and use that as
            # the source of the .cc_num here. This is fine -- a left and right
            # split of the same node should be in the same component, so this
            # really shouldn't make a difference...
            rc_node_cc_num = nodename2objs[rc_name][0].cc_num

            if candidate_twin_cc_num is None:
                # this is the first node we're looking at in this cc
                candidate_twin_cc_num = rc_node_cc_num
                if candidate_twin_cc_num == cc.cc_num:
                    # okay, so this node's RC is actually in the same
                    # component. This tells us that this component is
                    # "strand-mixed", so it is not redundant.
                    return None
            else:
                if candidate_twin_cc_num != rc_node_cc_num:
                    # Okay, so the RCs of the nodes in this component
                    # ended up in MULTIPLE other components. This
                    # implies that all three of these components
                    # (this cc, candidate_twin_cc_num, and
                    # rc_node_cc_num) are not redundant. (This could
                    # also be triggered if rc_node_cc_num == cc.cc_num,
                    # I guess, in which case there are just two
                    # distinct components involved here.)
                    #
                    # NOTE: it may save some time to tell the caller that
                    # all three of these components should be marked
                    # redundant, but that requires restructuring this...
                    # if it is a bottleneck we can refactor this
                    return None

                # If we've gotten to this branch, this means that this is not
                # the first node we've seen in this component, and that the
                # component in which its reverse-complementary node is
                # contained is consistent with all others that we've seen so
                # far. Keep going through the nodes in this component.
        else:
            # Node "n" has no reverse complement, weirdly enough. This
            # means that this component is nonredundant. This can
            # happen if you just remove some stuff from an "explicit"
            # file (e.g. FASTG / DOT).
            return None

    # If we've made it here, all of the nodes in cc have reverse complements
    # in this one component!
    return candidate_twin_cc_num


def get_candidate_twin_cc_num_from_edges(cc, userspecifiededgeid2obj):
    """Looks at the (real) edges in a Component to determine a possible twin.

    This is an alternate version of get_candidate_twin_cc_num_from_nodes(),
    but designed ONLY for Flye DOT graphs. (I mean it should also work for
    LJA DOT graphs, but for those you should still use
    get_candidate_twin_cc_num_from_nodes(), because nodes have an orientation
    in those -- this means that in the obscure case that you have components
    with zero edges, we will still look at node orientations to determine
    component redundancy.)

    See https://github.com/marbl/MetagenomeScope/issues/401 for details.

    Parameters
    ----------
    cc: Component

    userspecifiededgeid2obj: dict of str -> Edge

    Returns
    -------
    int or None
    """
    # You really shouldn't have zero-edge components in a Flye DOT graph,
    # but I GUESS we can allow this here (such components will be inherently
    # nonredundant). Um, I don't think this check is necessary (since otherwise
    # the below code would still end with returning None), but I'm keeping it
    # here for the sake of clarity (plus maybe I'll make this throw an error
    # later idk).
    if len(cc.edges) == 0:
        return None

    candidate_twin_cc_num = None

    for e in cc.edges:
        if not e.is_fake:
            eid = e.get_userspecified_id()
            rcid = name_utils.negate(eid)
            if rcid in userspecifiededgeid2obj:
                rc_edge_cc_num = userspecifiededgeid2obj[rcid].cc_num
                if candidate_twin_cc_num is None:
                    # this is the first edge we're looking at in cc
                    candidate_twin_cc_num = rc_edge_cc_num
                    if candidate_twin_cc_num == cc.cc_num:
                        # this edge's RC is in the same component
                        return None
                else:
                    if candidate_twin_cc_num != rc_edge_cc_num:
                        # RCs of edges in this component ended up in multiple
                        # other components
                        return None
            else:
                # this edge has no reverse-complement
                return None
    return candidate_twin_cc_num


def count_real_edge_info(cc, nodeid2obj, index_by_namepair=True):
    """Returns a Counter of some kind of edge info in a component.

    Parameters
    ----------
    cc: Component

    nodeid2obj: dict of int -> Node

    index_by_namepair: bool
        If True, the output Counter's keys will be pairs of node names.
        If False, the output Counter's keys will be user-specified Edge IDs.

    Returns
    -------
    Counter
        Maps edge info to an int of the number of occurrences we saw.
    """
    ctr = Counter()
    for e in cc.edges:
        if not e.is_fake:
            if index_by_namepair:
                info = (
                    nodeid2obj[e.new_src_id].basename,
                    nodeid2obj[e.new_tgt_id].basename,
                )
            else:
                # don't worry, this will throw an error if no such ID is set
                info = e.get_userspecified_id()
            ctr[info] += 1
    return ctr


def components_are_twins(cc, cc2, nodeid2obj, define_edges_by_nodenames=True):
    """Determines if two Components are "twins" of each other.

    Specifically, this checks (given components C1 and C2):

    - C1 and C2 have the same number of nodes
    - C1 and C2 have the same number of edges
    - Every edge E in C1 has a reverse-complementary edge -E in C2
        - How this is done depends on the define_edges_by_nodenames flag.

    Parameters
    ----------
    cc: Component

    cc2: Component

    nodeid2obj: dict of int -> Node

    define_edges_by_nodenames: bool
        If True, we count edges in the component (and determine reverse-
        complements) according to their source and target node names. So,
        an edge X -> Y is considered to be reverse-complementary to -Y -> -X.

        If False, we count edges and define reverse-complements going just
        by edge IDs. So, an edge E and an edge -E might be surrounded by
        completely different node names.

    Returns
    -------
    bool
        True if the Components are twins, False otherwise.

    Notes
    -----
    - This does not explicitly check that node names match up between these
      components (although tbh I think leaving define_edges_by_nodenames set to
      True basically has the same effect indicentally). In Flye DOT files, node
      names do not have orientation (see
      https://github.com/marbl/MetagenomeScope/issues/401); and in other types
      of graphs, you should have called get_candidate_twin_component_num()
      before this (which actually does check node names).

    - Using a Counter when define_edges_by_node_names is False is kind of lazy,
      since user-specified edge IDs are guaranteed to be unique by parse_dot().
      So this is comparing that like {E: 1, ...} and {-E: 1, ...} are unique,
      when really I guess we could just be comparing lists of IDs. I dunno.
      If this REALLY ends up being a bottleneck we can refactor this.
    """
    if (
        cc.num_full_nodes == cc2.num_full_nodes
        and cc.num_real_edges == cc2.num_real_edges
    ):
        # Counts match up; now check that edge details match up
        ectr1 = count_real_edge_info(
            cc, nodeid2obj, index_by_namepair=define_edges_by_nodenames
        )
        ectr2 = count_real_edge_info(
            cc2, nodeid2obj, index_by_namepair=define_edges_by_nodenames
        )

        if len(ectr1) == len(ectr2):
            for info in ectr1.keys():

                if define_edges_by_nodenames:
                    # info is a tuple (src name, tgt name)
                    rcinfo = (
                        name_utils.negate(info[1]),
                        name_utils.negate(info[0]),
                    )
                else:
                    # info is a string user-specified edge ID
                    rcinfo = name_utils.negate(info)

                if ectr1[info] != ectr2[rcinfo]:
                    return False
        else:
            return False

        # If we've made it here, then both the initial counts AND the edge
        # details match up. These components are twins!
        return True

    else:
        # oh no, they have different node or edge counts!
        # this could happen if for example cc2 contains both a perfect reverse-
        # complementary version of cc AND some other junk. Um, but probably I
        # doubt this will happen in practice much if at all lol
        return False
