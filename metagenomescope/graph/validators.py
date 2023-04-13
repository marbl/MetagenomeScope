# This file contains validation functions for potential patterns "starting"
# at a given node ID in an assembly graph, in addition to related utilities.
#
# Note that a single type of pattern (e.g. a bubble) may correspond to more
# one validation function here -- for example, we include functions for
# validating "bulges" as well as large bubbles, but both of them are (as of
# writing) labelled as "bubbles" in the user interface.


from metagenomescope.errors import WeirdError


class ValidationResults(object):
    """Stores the results of trying to validate a pattern.

    This class should make it easier to work with the results of different
    validation methods -- if we know that each method will return an instance
    of this object, it becomes easier to interpret the validation results
    (rather than worrying about if a method returns a 2-tuple, or a 4-tuple,
    etc).
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
        # Both the starting and ending node should be defined or None. We can't
        # have only one of them be defined. (^ = XOR operator)
        if (starting_node is None) ^ (ending_node is None):
            raise WeirdError(
                f"Starting node = {starting_node} but ending node = "
                f"{ending_node}?"
            )
        self.starting_node = starting_node
        self.ending_node = ending_node

    def __bool__(self):
        """Returns self.is_valid; useful for quick testing."""
        return self.is_valid

    def __repr__(self):
        """Returns a summary of these results for help with debugging.

        References
        ----------
        I feel like every few months I go through the obligatory pilgrimage of
        trying to remember if I should define __repr__(), __str__(), both, or
        if I should just give up and move to Antarctica. Based on moshez'
        excellent SO answer (https://stackoverflow.com/a/2626364) I have just
        defined __repr__() here, which should be more than sufficient.
        """
        if self.is_valid:
            suffix = ""
            if self.starting_node is not None:
                suffix = (
                    f" from {repr(self.starting_node)} to "
                    f"{repr(self.ending_node)}"
                )
            return f"Valid pattern of nodes {repr(self.nodes)}{suffix}"
        else:
            return "Not a valid pattern"


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
    - We only consider "simple" frayed ropes that look like

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

    - As long as the frayed rope follows the above structure, it is fine if it
      includes parallel edges (from a start node to the middle node, or from
      the middle node to the end node). These parallel edges should not be
      classified as "bulges," because bulges from (X, Y) are only valid if all
      of X's outgoing edges point to Y (and if all of Y's incoming edges come
      from X).
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
        # NOTE: We now allow cyclic frayed ropes. If you'd like to disallow
        # this, you can un-comment this.
        # for o in list(g.adj[n].keys()):
        #     # We know now that all of the ending nodes only have one
        #     # incoming node, but we don't know that about the starting
        #     # nodes. Make sure that this frayed rope isn't cyclical.
        #     if o in starting_node_ids:
        #         return ValidationResults()

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

         +---
         V   \
    2 -> 0 -> 1 -> 3

    ... 0 would still be the starting node for a valid cyclic chain of 0
    and 1, but 1 could not be the "starting node" (since it has two
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

    We could relax conditions 2 and 3 if desired, although this may complicate
    the pattern decomposition stuff. Notably, we also allow bulges where there
    exist edge(s) from E to S, to be consistent with how we allow cyclic
    bubbles (see https://github.com/marbl/MetagenomeScope/issues/241 for
    discussion).
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
                return ValidationResults(
                    True,
                    [starting_node_id, ending_node_id],
                    starting_node_id,
                    ending_node_id,
                )
    return ValidationResults()


def is_valid_bubble(g, starting_node_id):
    r"""Validates a (super)bubble starting at a node in a graph.

    Parameters
    ----------
    g: nx.MultiDiGraph
    starting_node_id: str

    Returns
    -------
    ValidationResults

    Notes
    -----
    - If there is a bubble starting at the start node, but it
      contains other bubbles within it, then this'll just return a
      minimal bubble (not starting at starting_node_id). It's
      expected that hierarchical decomposition will mean that we'll
      revisit starting_node_id later.

       - That being said, we do not check for the case where this bubble
         contains a *bulge* that has not been detected and collapsed yet.
         (Ditto for chains, etc.) By the time you call this function, you
         should have already ran at least one round of bulge and chain
         detection on the graph.

    - Previously, we used separate functions for validating 3-node bubbles
      (e.g. 0 ---------> 2) and simple bubbles (e.g. 0 ---> 1 --> 3).
             \          /                             \          /
              \--> 1 --/                               \--> 2 --/
      However, this is Kind Of Silly, because these types of structures would
      both also be identified by the Onodera 2013 superbubble validation code.
      To reduce code redundancy and probably save time, these two validation
      functions are superseded by this function (which was previously named
      is_valid_superbubble()). (Bulges still have their own validation function
      because those are not identified by is_valid_bubble(), tho.)

    - Similarly to how the frayed rope validation function allows for a frayed
      rope to contain parallel edges, we also allow for bubbles to contain
      parallel edges. (Although, as mentioned above, if this graph contains a
      bulge -- i.e. it has parallel edges between two nodes, *and* these two
      nodes actually are a bulge as defined by is_valid_bulge() -- then we
      will ignore this bulge, and just return the larger bubble structure. You
      can account for this by making sure that all possible bulges have been
      identified in the graph by the time you call this function.)

    References
    ----------
    This algorithm is adapted from Onodera et al. 2013:
    https://arxiv.org/pdf/1307.7925.pdf
    """
    verify_node_in_graph(g, starting_node_id)

    # MgSc-specific thing: if the starting node only has outgoing edge(s) to
    # one node, then this starting node isn't the start of a bubble. (It could
    # be the start of a chain or bulge, maybe, if its one outgoing node has no
    # incoming edges from other nodes.)
    #
    # We don't guarantee that the graph is a unipath graph; I believe that this
    # is an assumption of Onodera 2013's algorithm. This is why we impose this
    # restriction. (Otherwise, I found that weird stuff was getting called
    # as a bubble in the test Velvet E. coli graph.)
    if len(g.adj[starting_node_id]) < 2:
        return ValidationResults()

    # From section 3 of Onodera 2013:
    #
    # - Nodes are "visited" if they have already been visited in the main
    #   portion of the while loop below.
    #
    # - Nodes are "seen" if at least one of the node's parents has been
    #   visited.
    #
    # (A node can only have one label at a time -- there are multiple ways
    # to set this up; what we do here is just enforce this by storing node
    # labels, both visited and seen, in a single structure. That way, if we
    # e.g. mark a node as visited, then that automatically overrides that
    # node's previous label [e.g. seen].)
    #
    # ALSO UHHHH coming back to this code much later: node X is a "parent" of
    # node Y if there exist edge(s) X --> Y, right? (And Y is a "child" of X.)
    # The Onodera 2013 paper uses this parent/child notation extensively.
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
            # per the definitions outlined in Onodera 2013 superbubbles must
            # be acyclic. So we abort. (Although, that being said, we allow
            # the "ending node" (or "exit node," or "sink node," or whatever
            # you wanna call it... including all of that here for the sake of
            # anyone grepping through this code) to have edge(s) to the
            # starting node. See below.)
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
        # the only vertex marked as seen, then it's the exit (aka ending) node
        # of the bubble!
        seen_node_ids = [n for n in nodeid2label if nodeid2label[n] == "seen"]
        if len(S) == 1 and len(seen_node_ids) == 1:
            t = S.pop()
            if t != seen_node_ids[0]:
                raise WeirdError("Something went really wrong...?")

            # What if there are edge(s) from t to the starting node?
            # Onodera et al. explicitly do not identify bubbles where this is
            # the case, but here we *do* identify these sorts of bubbles. If
            # you'd like to prevent this, you can comment out the block below.
            # if starting_node_id in g.adj[t]:
            #     return ValidationResults()

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
                    out = is_valid_bubble(g, c)
                    if out:
                        return out

            # If the checks above succeeded, this is a valid
            # superbubble! Nice.
            return ValidationResults(True, composite, starting_node_id, t)

    return ValidationResults()


def not_single_edge(g, adj_view):
    """Returns True if an AdjacencyView doesn't describe exactly 1 edge.

    This accounts for two cases:
    - The case where there are != 1 adjacent nodes
    - The case where there is just one adjacent node, but there are parallel
      edges between this node and the node described by this AdjacencyView

    Parameters
    ----------
    g: nx.MultiDiGraph

    adj_view: nx.classes.coreviews.AdjacencyView
        The result of g.pred[n] or g.adj[n], where n is a node in g.
        g.pred refers to the incoming adjacencies of n; g.adj refers to the
        outgoing adjacencies of n.

    Returns
    -------
    bool
    """
    # Let's say that adj_view was given to us from g.pred[n].
    # If len(adj_view) != 1, then n has incoming edges from multiple nodes.
    # If len(adj_view) == 1 but the other gross condition is true, then n has
    # parallel edges from a single node. (I don't think there can be 0 edges
    # between this node and n, unless the AdjacencyView is malformed, but we
    # detect this anyway I guess.)
    # This explanation also works for g.adj[n]; just swap out "incoming" and
    # "from" with "outgoing" and "to" in the above text.
    return len(adj_view) != 1 or len(adj_view[list(adj_view)[0]]) != 1


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
    - THIS FINDS THE LONGEST POSSIBLE CHAIN that includes the starting node
      (herein referred to as "s" for brevity), if a Chain exists beginning at
      s.

      In other words: if we find that no Chain exists starting at s then we do
      not identify a valid Chain here, but if we do find that a Chain does
      exist starting at s then we traverse "backwards" to find the longest
      possible chain including s. (This way, if this function returns a chain,
      it's guaranteed to be "maximal.")

      If "s" is really present in a chain (as the final node), then that's fine
      -- we should come back to this later when running this function on
      another node earlier on in that chain.

      IF THIS IS ACTUALLY A CYCLIC CHAIN (i.e. the end node of the chain has an
      edge to the start node of the chain), we will not identify a valid Chain
      here. These sorts of cases should be caught when looking for cyclic
      chains.

      IDEALLY there would be a preexisting function in NetworkX that
      computes this, but I wasn't able to find something that does this.
      If you're aware of another library's implementation of this sort of
      thing, let me know! It'd be nice to avoid duplication of effort.

    - Chains cannot contain parallel edges. If a region of the graph would be a
      chain, but it just happens to contain some parallel edges, then these
      parallel edges should first be collapsed into bulges -- the resulting
      region should then be a chain.
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
        pred = g.pred[curr_node_id]
        if not_single_edge(g, pred):
            # The chain has ended, and this can't be the last node in it
            # (The node before this node, if applicable, is the chain's
            # actual end.)
            break

        adj = g.adj[curr_node_id]
        out_curr_node_ids = list(adj.keys())
        if not_single_edge(g, adj):
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

    pred = g.pred[starting_node_id]
    in_node_ids = list(pred.keys())
    if not_single_edge(g, pred):
        # We can't extend the chain "backwards" from the start,
        # so just return what we have currently. This is an "optimal" chain
        # ("optimal" in the sense that, of all possible chains that include
        # this starting node, this is the largest; note that my definition of
        # optimality ignores the whole hierarchical decomposition thing, and is
        # just considering the graph as seen by this function, please don't sue
        # me for messing this up, but I don't think I messed it up, why are you
        # still reading this comment).
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
        adj = g.adj[curr_node_id]
        if not_single_edge(g, adj):
            # Since this node has multiple outgoing edges, it can't be the
            # start of the chain. Therefore the previous node we were
            # looking at is the optimal starting node.
            break

        pred = g.pred[curr_node_id]
        in_curr_node_ids = list(pred.keys())

        if len(set(in_curr_node_ids) & set(chain_list)) > 0:
            # The chain "begins" cyclically, so we'll tag it as a
            # cyclic chain later on.
            return ValidationResults()

        if not_single_edge(g, pred):
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
