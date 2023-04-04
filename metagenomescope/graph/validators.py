# Validation methods for potential patterns starting at a given node ID in an
# assembly graph.


import networkx as nx
from metagenomescope.errors import WeirdError


class ValidationResults(object):
    """Stores the results of trying to validate a pattern.

    ... I guess this is more consistent to work with than returning a 2-tuple,
    or maybe sometimes a 4-tuple, or whatever.
    """

    def __init__(
        self,
        is_valid=False,
        nodes=[],
        starting_node=None,
        ending_node=None,
    ):
        """Initializes this object.

        Parameters
        ----------
        is_valid: bool
            True if the proposed pattern was valid; False otherwise.

        nodes: list
            If is_valid is True, contains a list of the nodes in the pattern;
            otherwise, this should be an empty list.

        starting_node: str or None
            If is_valid is True and if the pattern has a single defined start
            and end node (which is the case for all patterns except frayed
            ropes, at the moment), this should be the ID of the starting node
            in the pattern. Otherwise, this should be None.

        ending_node: str or None
            Like starting_node, but for the ending node of the pattern.
        """
        self.is_valid = is_valid
        self.nodes = nodes
        self.starting_node = starting_node
        self.ending_node = ending_node

    def __bool__(self):
        """Returns self.is_valid; useful for quick testing."""
        return self.is_valid


def verify_node_in_graph(g, node_id):
    """Raises a WeirdError if a node is not present in a graph."""
    if node_id not in g.nodes:
        raise WeirdError(
            f"Node {node_id} is not present in the graph's nodes? Something "
            "may have gone wrong during hierarchical decomposition."
        )


def is_valid_frayed_rope(g, starting_node_id):
    r"""Validates a frayed rope starting at a node in a graph.

    A frayed rope will have multiple starting nodes, of course -- this
    function doesn't care which of these is given (any is fine).

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    We only consider "simple" frayed ropes that look like

    s1 -\ /-> e1
         m
    s2 -/ \-> e2

    ...that is, frayed ropes containing only one middle node. There can
    be an arbitrary amount of start and end nodes defined (so long as
    there are >= 2 start/end nodes), though. (Also, the number of start
    and end nodes doesn't have to match up.)

    (We could explicitly try to search for frayed ropes containing a chain of
    middle nodes, but these chains should have already been collapsed by the
    time we call this function.)
    """
    verify_node_in_graph(g, starting_node_id)

    # If the starting node doesn't have exactly 1 outgoing node, fail
    if len(g.adj[starting_node_id]) != 1:
        return ValidationResults()

    # Get the tentative "middle" node in the rope
    middle_node_id = list(g.adj[starting_node_id].keys())[0]

    # Now, get all "starting" nodes (the incoming nodes on the middle node)
    starting_node_ids = list(g.pred[middle_node_id].keys())

    # A frayed rope must have multiple paths from which to converge to
    # the "middle node" section
    if len(starting_node_ids) < 2:
        return ValidationResults()

    # Ensure none of the start nodes have extraneous outgoing nodes
    for n in starting_node_ids:
        if len(g.adj[n]) != 1:
            return ValidationResults()

    # Now we know the start nodes are mostly valid. We'll still need to
    # check that each node in the rope is distinct, but that is done
    # later on -- after we've identified all the nodes in the tentative
    # rope.

    ending_node_ids = list(g.adj[middle_node_id].keys())

    # The middle node has to diverge to something for this to be a frayed
    # rope.
    if len(ending_node_ids) < 2:
        return ValidationResults()
    for n in ending_node_ids:
        # Check for extraneous incoming edges
        if len(g.pred[n]) != 1:
            return ValidationResults()
        for o in list(g.adj[n].keys()):
            # We know now that all of the ending nodes only have one
            # incoming node, but we don't know that about the starting
            # nodes. Make sure that this frayed rope isn't cyclical.
            if o in starting_node_ids:
                return ValidationResults()

    # Check the entire frayed rope's structure
    composite = starting_node_ids + [middle_node_id] + ending_node_ids

    # Verify all nodes in the frayed rope are distinct
    if len(set(composite)) != len(composite):
        return ValidationResults()

    # If we've made it here, this frayed rope is valid!
    return ValidationResults(True, composite)


def is_valid_cyclic_chain(g, starting_node_id):
    r"""Validates a cyclic chain "starting at" a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    Note that "starting_node_id" is sort of a misnomer, since some cyclic
    chains don't have a single starting node (e.g. isolated cycles, like
    0 -> 1 -> 0). Either 0 or 1 would be considered "starting nodes" for a
    valid cyclic chain in this example. However, in cases like...

          +--
          V  \
    2 -> 0 -> 1 -> 3

    ... 0 would still be the starting node for a valid cyclic chain of 0
    and 1, but 1 would not be the "starting node" (since it has two
    separate outgoing nodes).
    """
    verify_node_in_graph(g, starting_node_id)
    s_outgoing_node_ct = len(g.adj[starting_node_id])
    if len(g.pred[starting_node_id]) == 0 or s_outgoing_node_ct == 0:
        # If the starting node has no incoming or no outgoing nodes, it
        # can't be in a cycle!
        return ValidationResults()

    # TODO CHANGE THIS
    # Edge case: we identify single nodes with loops to themselves.
    # If the start node has multiple outgoing edges but no reference to
    # itself, then it isn't the start node for a cycle. (It could very
    # well be the "end node" of another cycle, but we would eventually
    # test that node for being a cycle later on.)
    if starting_node_id in list(g.adj[starting_node_id].keys()):
        # Valid whether s has 1 or >= 1 outgoing edges
        return ValidationResults(
            True, [starting_node_id], starting_node_id, starting_node_id
        )
    elif s_outgoing_node_ct > 1:
        # Although we allow singleton looped nodes to be cycles (and to
        # have > 1 outgoing nodes), we don't allow larger cycles to be
        # constructed from a start node with > 1 outgoing nodes (since
        # these are simple chain-like cycles, as discussed above).
        return ValidationResults()

    # Ok, things look promising. Now, we iterate "down" through the cyclic
    # chain to see what it's composed of.
    cch_list = [starting_node_id]
    curr = list(g.adj[starting_node_id].keys())[0]
    while True:
        if len(g.pred[curr]) != 1:
            # The cyclic chain has ended, and this can't be the last node
            # in it -- but since the cyclic chain didn't "loop back" yet,
            # we weren't able to identify an applicable cyclic chain
            # (The node before this node, if applicable, is the cycle's
            # actual end.)
            return ValidationResults()
        if len(g.adj[curr]) != 1:
            # Like above, this means the "end" of the cyclic chain, but it
            # could mean the cyclic chain is valid.
            # NOTE that at this point, if curr has an outgoing edge to a
            # node in cch_list, it has to be to the starting node.
            # This is because we've already checked every other node in
            # cch_list to ensure that every non-starting node has
            # only 1 incoming node.
            if len(g.adj[curr]) > 1 and starting_node_id in list(
                g.adj[curr].keys()
            ):
                return ValidationResults(
                    True, cch_list + [curr], starting_node_id, curr
                )
            else:
                # If we didn't loop back to start at the end of the
                # cyclic chain, we never will for this particular
                # structure. So just return False.
                return ValidationResults()

        # We know curr has one incoming and one outgoing edge. If its
        # outgoing edge is to the starting node, then we've found a cycle.
        if list(g.adj[curr].keys())[0] == starting_node_id:
            return ValidationResults(
                True, cch_list + [curr], starting_node_id, curr
            )

        # If we're here, the cyclic chain is still going on -- the next
        # node to check is not already in cch_list.
        cch_list.append(curr)
        curr = list(g.adj[curr].keys())[0]

    # If we're here then something went terribly wrong
    raise WeirdError(
        (
            "Sorry! Something went terribly wrong during cyclic chain "
            "detection using a tentative starting node ID of {}. Please "
            "raise an issue on the MetagenomeScope GitHub page, and "
            "include the assembly graph file you're using as input."
        ).format(starting_node_id)
    )


def is_bubble_boundary_node_invalid(g, node_id):
    """Returns True if the node is a collapsed pattern that is NOT a
    bubble, False otherwise.

    Basically, the purpose of this is rejecting things like frayed
    ropes that don't make sense as the start / end nodes of bubbles.
    """
    verify_node_in_graph(g, node_id)
    if "pattern_type" in g.nodes[node_id]:
        return g.nodes[node_id]["pattern_type"] != "bubble"
    return False


def is_valid_bulge(g, starting_node_id):
    r"""Validates a simple bulge starting at a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    We say that there exists a simple bulge on nodes (S, E) if all of the
    following conditions are met:

    1. There exist at least two edges from S --> E.
    2. All of S's outgoing edges point to E.
    3. All of E's incoming edges come from S.
    4. There is not an edge from E to S.

    We could relax conditions 2, 3, and 4 if desired, although it may
    complicate the pattern decomposition stuff. So, for now, let's stick with
    these strict "simple" bulges.
    """
    verify_node_in_graph(g, starting_node_id)
    adj = g.adj[starting_node_id]
    if len(adj) == 1:
        # Condition 2 is met
        ending_node_id = list(adj)[0]
        if len(g.pred[ending_node_id]) == 1:
            # Condition 3 is met
            if len(adj[ending_node_id]) > 1:
                # Condition 1 is met
                if starting_node_id not in g.adj[ending_node_id]:
                    # Condition 4 is met
                    return ValidationResults(
                        True,
                        [starting_node_id, ending_node_id],
                        starting_node_id,
                        ending_node_id,
                    )
    return ValidationResults()


def is_valid_3node_bubble(g, starting_node_id):
    r"""Validates a 3-node bubble starting at a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    The bubbles we try to detect look like:

      /-m-\
     /     \
    s-------e

    Due to the nature of hierarchical pattern decomposition, we only
    allow the middle "path" to be a single node. This is still broad
    enough to allow for bubbles with a linear path of multiple nodes
    in the middle, e.g.

      /-m1-m2-m3-\
     /            \
    s--------------e

    ... since we assume that this path has already been collapsed into a
    chain.
    """
    # NOTE - this is unneeded if we keep calling
    # is_bubble_boundary_node_invalid(), but i think we'll phase that out soon
    verify_node_in_graph(g, starting_node_id)
    # Starting node must be either an uncollapsed node or another bubble
    if is_bubble_boundary_node_invalid(g, starting_node_id):
        return ValidationResults()

    # The starting node in a 3-node bubble must have exactly 2 out edges
    out_node_ids = list(g.adj[starting_node_id].keys())
    if len(out_node_ids) != 2:
        return ValidationResults()

    # Of the two nodes the start node points to, one must have two incoming
    # edges (this is the end node) and the other must have one incoming
    # edge (this is the middle node)
    m = None
    e = None
    for out_node in out_node_ids:
        if len(g.pred[out_node]) == 2 and e is None:
            e = out_node
        elif len(g.pred[out_node]) == 1 and m is None:
            m = out_node
        else:
            return ValidationResults()

    # We tentatively have a valid 3-node bubble, but we need to do some
    # more verification.

    # Verify that end node is either an uncollapsed node or another bubble
    if is_bubble_boundary_node_invalid(g, e):
        return ValidationResults()

    # First, check that the middle node points to the end node: if not,
    # then that's a problem!
    if m not in g.pred[e]:
        return ValidationResults()

    # Also, check that the middle node has exactly 1 outgoing edge (this
    # would imply that it points outside of the bubble, which we don't
    # allow)
    if len(g.adj[m]) != 1:
        return ValidationResults()

    # Reject cyclic bubbles and/or bubbles where the end node points to the
    # starting node, the middle node, or itself
    # NOTE: for now, allowing end node to point to start node.
    if len(set([m, e]) & set(g.adj[e])) > 0:
        return ValidationResults()

    # Ensure that all nodes in the bubble are distinct (protects against
    # weird cases like s -> m -> s where the starting node is the end node)
    composite = [starting_node_id, m, e]
    if len(set(composite)) != 3:
        return ValidationResults()

    # If we've gotten here, then we know that this is a valid bubble.
    return ValidationResults(True, composite, starting_node_id, e)


def is_valid_bubble(g, starting_node_id):
    r"""Validates a simple bubble starting at a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    Here, we only consider "simple" bubbles that look like

      /-m1-\        /-m1-\
     /      \      /      \
    s        e or s---m2---e  ..., etc.
     \      /      \      /
      \-m2-/        \-m3-/

    That is, we expect that this each path between the start
    node and the end node must only have one "middle" node, although
    there can be an arbitrary (>= 2) amount of such paths.

    This is because we assume that other complexities, such as
    "chains" (e.g. a middle path actually contains n nodes where
    m1 -> m2 -> ... mn), have already been collapsed.

    Also, note that we don't detect 3-node bubbles here (those are
    detected by is_valid_3node_bubble()).

    Lastly, we don't currently detect bubbles where there's an edge
    directly between the start and end node. ...but these should be
    possible to detect with more robust bubble-finding techniques.
    """
    verify_node_in_graph(g, starting_node_id)

    # For now, bubbles can only start with 1) uncollapsed nodes or 2) other
    # bubbles (which'll cause us to duplicate stuff)
    if is_bubble_boundary_node_invalid(g, starting_node_id):
        return ValidationResults()

    # The starting node in a bubble obviously must have at least 2 outgoing
    # edges. If not, we can bail early on.
    m_node_ids = list(g.adj[starting_node_id].keys())
    if len(m_node_ids) <= 1:
        return ValidationResults()

    # Will be recorded here (if we get to it...)
    ending_node_id = None

    # Each outgoing node from the "starting node" represents a possible
    # path through this bubble.
    for m in m_node_ids:
        # ... And of course, each node on this path can't have extra
        # incoming nodes (which would be from outside of the bubble) or
        # extra outgoing nodes (which would represent non-bubble-like
        # branching behavior).
        if len(g.pred[m]) != 1 or len(g.adj[m]) != 1:
            return ValidationResults()

        # Ok, so this tentatively seems like a valid path.
        outgoing_node_id_from_m = list(g.adj[m].keys())[0]

        # If this is the first "middle" node we're checking, then record
        # its outgoing node as the tentative "ending" node
        if ending_node_id is None:
            ending_node_id = outgoing_node_id_from_m
        # If we've already checked another middle node, verify that this
        # middle node converges to the same "ending"
        elif ending_node_id != outgoing_node_id_from_m:
            return ValidationResults()

    # Check that the ending node is reasonable

    # If the ending node is a non-bubble pattern, reject this (for now).
    if is_bubble_boundary_node_invalid(g, ending_node_id):
        return ValidationResults()

    # If the ending node has any incoming nodes that aren't in m_node_ids,
    # reject this bubble.
    if set(g.pred[ending_node_id]) != set(m_node_ids):
        return ValidationResults()

    # Reject cyclic bubbles (although we could allow this if people want
    # it, I guess?)
    # if starting_node_id in list(g.adj[ending_node_id].keys()):
    #     return ValidationResults()

    # Ensure that all nodes in the bubble are distinct (protects against
    # weird cases like
    #
    #   -> m1 ->
    # s -> m2 -> s
    #
    # Where the starting node is the ending node, etc.)
    composite = [starting_node_id] + m_node_ids + [ending_node_id]
    if len(set(composite)) != len(composite):
        return ValidationResults()

    # If we've gotten here, then we know that this is a valid bubble.
    return ValidationResults(True, composite, starting_node_id, ending_node_id)


def is_valid_superbubble(g, starting_node_id):
    r"""Validates a superbubble starting at a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    If there is a superbubble starting at the start node, but it
    contains other superbubbles within it, then this'll just return a
    minimal superbubble (not starting at starting_node_id). It's
    expected that hierarchical decomposition will mean that we'll
    revisit this question later.

    References
    ----------
    This algorithm is adapted from Onodera et al. 2013:
    https://arxiv.org/pdf/1307.7925.pdf
    """
    verify_node_in_graph(g, starting_node_id)
    # Starting node must be either an uncollapsed node or another bubble
    if is_bubble_boundary_node_invalid(g, starting_node_id):
        return ValidationResults()

    # MgSc-specific thing: if the starting node only has one outgoing
    # edge, then it should be collapsed into a chain, not a bubble.
    # There might be a bubble later on down from it, but it isn't the
    # start of a bubble. (We don't guarantee that the graph is
    # a unipath graph, which is an assumption of Onodera 2013's algorithm I
    # think -- hence our need to impose this restriction. Otherwise, I
    # found that weird stuff was getting called as a bubble in the test
    # Velvet E. coli graph, and it was breaking my code, so I added this
    # in.)
    if len(g.adj[starting_node_id]) < 2:
        return ValidationResults()

    # From section 3 of Onodera 2013:
    # Nodes are visited if they have already been visited in the main
    # portion of the while loop below.
    # Nodes are seen if at least one of the node's parents has been
    # visited.
    # (A node can only have one label at a time -- there are multiple ways
    # to set this up; what we do here is just enforce this by storing node
    # labels, both visited and seen, in a single structure. That way, if we
    # e.g. mark a node as visited, then that automatically overrides that
    # node's previous label (e.g. seen).
    nodeid2label = {}

    S = set([starting_node_id])
    while len(S) > 0:
        v = S.pop()

        # Mark v as visited
        nodeid2label[v] = "visited"

        # If v doesn't have any outgoing edges, abort: this is a "tip".
        if len(g.adj[v]) == 0:
            return ValidationResults()

        # Otherwise, let's go through v's "children".
        for u in g.adj[v]:
            # if v points to the starting node then there is a cycle, and
            # per the definitions outlined Onodera 2013 superbubbles must
            # be acyclic. So we abort.
            if u == starting_node_id:
                return ValidationResults()

            # Mark u as "seen"
            nodeid2label[u] = "seen"

            # If all of u's parents have been visited, let's go visit u.
            all_parents_visited = True
            for p in g.pred[u]:
                if p not in nodeid2label or nodeid2label[p] != "visited":
                    all_parents_visited = False
                    break
            if all_parents_visited:
                S.add(u)

        # If just one vertex (let's call it t) is left in S, and if t is
        # the only vertex marked as seen, then it's the exit node of the
        # bubble! (aka the "end node".)
        seen_node_ids = [n for n in nodeid2label if nodeid2label[n] == "seen"]
        if len(S) == 1 and len(seen_node_ids) == 1:
            t = S.pop()
            if t != seen_node_ids[0]:
                raise ValueError("Something went really wrong...?")

            # If there's an edge from t to the starting node, then this
            # superbubble is cyclic.
            # We actually allow this, although Onodera et al. do not.
            # Partially because this helps with hierarchical decomp stuff,
            # and partially because I don't think there's a problem with
            # this...? but idk. Up for debate.
            # if starting_node_id in g.adj[t]:
            #     return ValidationResults()

            # A quick MetagenomeScope-specific check: Verify that end node
            # is either an uncollapsed node or another bubble
            if is_bubble_boundary_node_invalid(g, t):
                return ValidationResults()

            composite = list(nodeid2label.keys())

            # This part was not present in Onodera 2013. They make the
            # claim of "minimality," but only with respect to superbubbles
            # that begin at a specific starting node -- as far as I can
            # tell they don't account for the case when one superbubble
            # completely contains another (see for example Fig. 2a of
            # Nijkamp et al. 2013). To account for this, we just rerun the
            # superbubble detection algorithm on all non-start/end nodes
            # within a superbubble, and if we find a hit we just return
            # THAT superbubble. (Since we use recursion, the superbubble
            # returned here should be guaranteed to not contain any other
            # ones.)
            #
            # This does not mean we're abandoning this superbubble - due
            # to the hierarchical decomp stuff, we'll come back to it
            # later!
            #
            # This is of course super inefficient in theory. However, since
            # this repeated check only gets run once we DO find a
            # superbubble, I don't think it will be too slow. Sorta similar
            # to how the superbubble detection algorithms for metaFlye are
            # slow in theory but in practice are pretty fast.
            for c in composite:
                if c != t and c != starting_node_id:
                    out = is_valid_superbubble(g, c)
                    if out:
                        return out

            # If the checks above succeeded, this is a valid
            # superbubble! Nice.
            return ValidationResults(True, composite, starting_node_id, t)

    return ValidationResults()


def is_valid_chain(g, starting_node_id):
    r"""Validates a chain "starting at" a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    THIS FINDS THE LONGEST POSSIBLE CHAIN that includes the starting node
    (herein referred to as "s" for brevity), if a Chain exists beginning at s.

    In other words: if we find that no Chain exists starting at s then we do
    not identify a valid Chain here, but if we do find that a Chain does
    exist starting at s then we traverse "backwards" to find the longest
    possible chain including s. (This way, if this function returns a chain,
    it's guaranteed to be "maximal.")

    If "s" is really present in a chain (as the final node), then that's fine
    -- we should come back to this later when running this function on another
    node earlier on in that chain.

    IF THIS IS ACTUALLY A CYCLIC CHAIN (i.e. the end node of the chain has an
    edge to the start node of the chain), we will not identify a valid Chain
    here. These sorts of cases should be caught when looking for cyclic chains.

    IDEALLY there would be a preexisting function in NetworkX that
    computes this, but I wasn't able to find something that does this.
    If you're aware of another library's implementation of this sort of
    thing, let me know! It'd be nice to avoid duplication of effort.
    """
    verify_node_in_graph(g, starting_node_id)
    out_node_ids = list(g.adj[starting_node_id].keys())
    # If the starting node doesn't have an outgoing edge to exactly one
    # node -- or even if it does, but if that node is itself -- then this
    # isn't a valid chain
    if len(out_node_ids) != 1 or out_node_ids[0] == starting_node_id:
        return ValidationResults()

    chain_list = [starting_node_id]
    curr_node_id = out_node_ids[0]
    chain_ends_cyclically = False
    # Iterate "down" through the chain
    while True:
        if len(g.pred[curr_node_id]) != 1:
            # The chain has ended, and this can't be the last node in it
            # (The node before this node, if applicable, is the chain's
            # actual end.)
            break

        out_curr_node_ids = list(g.adj[curr_node_id].keys())
        if len(out_curr_node_ids) != 1:
            # Like above, this means the end of the chain, but there are
            # multiple ways we can handle this.
            #
            # First, check to see if the chain ends cyclically (i.e. the
            # end node leads to the start node). If this is the case, we
            # say that this isn't a valid chain (instead, we'll later
            # identify this as a cyclic chain when looking for those).
            #
            # The reason we only check the start node from the end node
            # (and not any of the other nodes already in chain_list) is
            # that we already know that the other stuff in chain_list has
            # only one incoming node, etc.
            if (
                len(out_curr_node_ids) > 1
                and starting_node_id in out_curr_node_ids
            ):
                chain_ends_cyclically = True
            else:
                # If we made it here, then the chain does not end
                # cyclically! (But you could've figured that out without
                # this comment. :) So we can say that yes, this is a valid
                # chain, and this node is a valid end node.
                chain_list.append(curr_node_id)

            # Regardless of what we just decided to do, we break here;
            # we're done traversing the chain forwards.
            break

        # See the above comment re: cyclic outgoing edges -- same thing
        # here, but in the case where len(out_curr_node_ids) == 1.
        if out_curr_node_ids[0] == starting_node_id:
            chain_ends_cyclically = True
            break

        # If we made it all the way down here, the chain is still going on!
        chain_list.append(curr_node_id)
        curr_node_id = out_curr_node_ids[0]

    # At this point, we're done iterating down the chain.
    if len(chain_list) <= 1 or chain_ends_cyclically:
        # There wasn't a Chain starting at the specified node ID.
        # There might be a Chain that starts before this node that
        # *includes* this node as an end node, but we don't bother with
        # that; we should get to it eventually.
        # Similarly, there might be a Cyclic Chain starting at the
        # specified node ID, but again we will Get To It Later (tm).
        return ValidationResults()

    in_node_ids = list(g.pred[starting_node_id].keys())
    if len(in_node_ids) != 1:
        # We can't extend the chain "backwards" from the start,
        # so just return what we have currently. This is an "optimal" chain
        # ("optimal" in the sense that, of all possible chains that include
        # this starting node, this is the largest).
        return ValidationResults(
            True, chain_list, starting_node_id, chain_list[-1]
        )

    # If we're here, we know a Chain exists starting at starting_node_id.
    # The question is: can it be extended in the opposite direction to
    # start at a node "before" starting_node_id? To figure that out, we
    # basically just repeat what we did above but in reverse.
    backwards_chain_list = []
    curr_node_id = in_node_ids[0]
    while True:
        if len(g.adj[curr_node_id]) != 1:
            # Since this node has multiple outgoing edges, it can't be the
            # start of the chain. Therefore the previous node we were
            # looking at is the optimal starting node.
            break

        in_curr_node_ids = list(g.pred[curr_node_id].keys())

        if len(set(in_curr_node_ids) & set(chain_list)) > 0:
            # The chain "begins" cyclically, so we'll tag it as a
            # cyclic chain later on.
            return ValidationResults()

        if len(in_curr_node_ids) != 1:
            # This node has multiple (or 0) incoming edges, so it's
            # the optimal start of the chain.
            backwards_chain_list.append(curr_node_id)
            break

        # At this point, we can safely continue moving "back".
        backwards_chain_list.append(curr_node_id)
        curr_node_id = in_curr_node_ids[0]

    # At this point, we're done iterating "backwards" up the chain.

    if backwards_chain_list == []:
        # There wasn't a more optimal starting node. Oh well!
        return ValidationResults(
            True, chain_list, starting_node_id, chain_list[-1]
        )

    # If we're here, we found a more optimal starting node. Nice!
    backwards_chain_list.reverse()
    return ValidationResults(
        True,
        backwards_chain_list + chain_list,
        backwards_chain_list[0],
        chain_list[-1],
    )
