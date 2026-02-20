from .. import ui_utils, config
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
            f"Trying to split node {nodeid2obj[nid0]}, which has at least one "
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
