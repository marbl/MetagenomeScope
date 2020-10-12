from copy import deepcopy
import networkx as nx
from .. import assembly_graph_parser

# from .basic_objects import Node, Edge


class AssemblyGraph(object):
    """Representation of an input assembly graph.

    This contains information about the top-level structure of the graph:
    including nodes, edges, and connected components.

    In fancy object-oriented programming terminology, this class is a
    "composition" with a NetworkX DiGraph. This really just means that,
    rather than subclassing nx.DiGraph, this class just contains an instance
    of nx.DiGraph (self.digraph) that we occasionally delegate to.

    CODELINK: This "composition" paradigm was based on this post:
    https://www.thedigitalcatonline.com/blog/2014/08/20/python-3-oop-part-3-delegation-composition-and-inheritance/
    """

    def __init__(self, filename):
        """Parses the input graph file and initializes the AssemblyGraph."""
        self.filename = filename
        self.nodes = []
        self.edges = []
        self.components = []
        # Each entry in these structures will be the unique ID of a node group
        # pointing to a list containing all of the node IDs in the node group
        # in question (these node IDs can include other group IDs!)
        #
        # NOTE that these patterns will only be "represented" in
        # self.decomposed_digraph; self.digraph represents the literal graph
        # structure as initially parsed.
        self.chains = {}
        self.cyclic_chains = {}
        self.bubbles = {}
        self.frayed_ropes = {}

        # TODO extract common node/edge attrs from parse(). There are various
        # ways to do this, from elegant (e.g. create classes for each filetype
        # parser that define the expected node/edge attrs) to patchwork (just
        # return 3 things from each parsing function and from parse(), where
        # the last two things are tuples of node and edge attrs respectively).
        self.digraph = assembly_graph_parser.parse(self.filename)
        self.reindex_digraph()

        # Number of nodes in the graph, including patterns and duplicate nodes.
        # Used for assigning new unique node IDs.
        self.num_nodes = len(self.digraph)

        self.decomposed_digraph = None
        # Poss TODO: Convert self.digraph into collections of Node/Edge objs?
        # So one option is doing this immediately after creating self.digraph,
        # and another option is deferring this until just before layout (or
        # even not doing this at all, and rewriting layout to not use my custom
        # Node/Edge/... types).
        # So, at least *a fair portion* of the custom Node/Edge classes is
        # rendered unnecessary by the fact that we're using an actual graph
        # library instead of implementing DFS, adjacency, etc. custom (why did
        # I ever think that was a good idea...?) however, it'll likely be
        # easiest to still use the custom Node/Edge classes for doing layout
        # crap, as well as storing other weird stuff.
        # for node in self.digraph.nodes:
        #     pass

    def reindex_digraph(self):
        """Assigns every node in the graph a unique integer ID, and adds a
        "name" attribute containing the original ID. This unique integer ID
        should never be shown to the user, but will be used for things like
        layout and internal storage of nodes. This way, we can have multiple
        nodes with the same name without causing a problem.
        """
        self.digraph = nx.convert_node_labels_to_integers(
            self.digraph, label_attribute="name"
        )

    def get_new_node_id(self):
        """Returns an int guaranteed to be usable as a unique new node ID."""
        new_id = self.num_nodes
        self.num_nodes += 1
        return new_id

    @staticmethod
    def is_valid_frayed_rope(g, starting_node_id):
        r"""Returns a 2-tuple of (True, a list of all the nodes in the f. rope)
        if a frayed rope with the given start node would be valid. Returns a
        2-tuple of (False, None) if such a frayed rope would be considered
        invalid.

        NOTE that we only consider "simple" frayed ropes that look like

        s1 -\ /-> e1
             m
        s2 -/ \-> e2

        ...that is, frayed ropes containing only one middle node. There can
        be an arbitrary amount of start and end nodes defined (so long as
        there are >= 2 start/end nodes), though. (Also, the number of start
        and end nodes doesn't have to match up.)
        """

        # If the starting node doesn't have exactly 1 outgoing node, fail
        if len(g.adj[starting_node_id]) != 1:
            return False, None

        # Get the tentative "middle" node in the rope
        middle_node_id = list(g.adj[starting_node_id].keys())[0]

        # Now, get all "starting" nodes (the incoming nodes on the middle node)
        starting_node_ids = list(g.pred[middle_node_id].keys())

        # A frayed rope must have multiple paths from which to converge to
        # the "middle node" section
        if len(starting_node_ids) < 2:
            return False, None

        # Ensure none of the start nodes have extraneous outgoing nodes
        for n in starting_node_ids:
            if len(g.adj[n]) != 1:
                return False, None

        # Now we know the start nodes are mostly valid. We'll still need to
        # check that each node in the rope is distinct, but that is done
        # later on -- after we've identified all the nodes in the tentative
        # rope.

        ending_node_ids = list(g.adj[middle_node_id].keys())

        # The middle node has to diverge to something for this to be a frayed
        # rope.
        if len(ending_node_ids) < 2:
            return False, None
        for n in ending_node_ids:
            # Check for extraneous incoming edges
            if len(g.pred[n]) != 1:
                return False, None
            for o in list(g.adj[n].keys()):
                # We know now that all of the ending nodes only have one
                # incoming node, but we don't know that about the starting
                # nodes. Make sure that this frayed rope isn't cyclical.
                if o in starting_node_ids:
                    return False, None

        # Check the entire frayed rope's structure
        composite = starting_node_ids + [middle_node_id] + ending_node_ids

        # Verify all nodes in the frayed rope are distinct
        if len(set(composite)) != len(composite):
            return False, None

        # If we've made it here, this frayed rope is valid!
        return True, composite

    @staticmethod
    def is_valid_cyclic_chain(g, starting_node_id):
        """Identifies the cyclic chain that "starts at" a given starting
        node, if such a cyclic chain exists. Returns (True, [nodes]) if
        such a cyclic chain exists (where [nodes] is a list of all the
        node IDs in the cyclic chain), and (False, None) otherwise.
        """
        s_outgoing_node_ct = len(g.adj[starting_node_id])
        if len(g.pred[starting_node_id]) == 0 or s_outgoing_node_ct == 0:
            # If the starting node has no incoming or no outgoing nodes, it
            # can't be in a cycle!
            return False, None
        # Edge case: we identify single nodes with loops to themselves.
        # If the start node has multiple outgoing edges but no reference to
        # itself, then it isn't the start node for a cycle. (It could very
        # well be the "end node" of another cycle, but we would eventually
        # test that node for being a cycle later on.)
        if starting_node_id in list(g.adj[starting_node_id].keys()):
            # Valid whether s has 1 or >= 1 outgoing edges
            return True, [starting_node_id]
        elif s_outgoing_node_ct > 1:
            # Although we allow singleton looped nodes to be cycles (and to
            # have > 1 outgoing nodes), we don't allow larger cycles to be
            # constructed from a start node with > 1 outgoing nodes (since
            # these are simple chain-like cycles, as discussed above).
            return False, None

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
                return False, None
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
                    return True, cch_list + [curr]
                else:
                    # If we didn't loop back to start at the end of the
                    # cyclic chain, we never will for this particular
                    # structure. So just return False.
                    return False, None

            # We know curr has one incoming and one outgoing edge. If its
            # outgoing edge is to the starting node, then we've found a cycle.
            if list(g.adj[curr].keys())[0] == starting_node_id:
                return True, cch_list + [curr]

            # If we're here, the cyclic chain is still going on -- the next
            # node to check is not already in cch_list.
            cch_list.append(curr)
            curr = list(g.adj[curr].keys())[0]

        # If we're here then something went terribly wrong
        raise RuntimeError(
            (
                "Sorry! Something went terribly wrong during cyclic chain "
                "detection using a tentative starting node ID of {}. Please "
                "raise an issue on the MetagenomeScope GitHub page, and "
                "include the assembly graph file you're using as input."
            ).format(starting_node_id)
        )

    @staticmethod
    def is_valid_3node_bubble(g, starting_node_id):
        r"""Returns a 4-tuple of (True, a list of all the nodes in the bubble,
           the starting node in the bubble, the ending node in the bubble)
           if a 3-node bubble defined at the given start node would be valid.
           Returns a 2-tuple of (False, None) if such a bubble would be
           considered invalid.

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
        # The starting node in a 3-node bubble must have exactly 2 out edges
        out_node_ids = list(g.adj[starting_node_id].keys())
        if len(out_node_ids) != 2:
            return False, None

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
                return False, None

        # We tentatively have a valid 3-node bubble, but we need to do some
        # more verification.

        # First, check that the middle node points to the end node: if not,
        # then that's a problem!
        if m not in g.pred[e]:
            return False, None

        # Also, check that the middle node has exactly 1 outgoing edge (this
        # would imply that it points outside of the bubble, which we don't
        # allow)
        if len(g.adj[m]) != 1:
            return False, None

        # Reject cyclic bubbles and/or bubbles where the end node points to the
        # starting node, the middle node, or itself
        if len(set([starting_node_id, m, e]) & set(g.adj[e])) > 0:
            return False, None

        # Ensure that all nodes in the bubble are distinct (protects against
        # weird cases like s -> m -> s where the starting node is the end node)
        composite = [starting_node_id, m, e]
        if len(set(composite)) != 3:
            return False, None

        # If we've gotten here, then we know that this is a valid bubble.
        return True, composite, starting_node_id, e

    @staticmethod
    def is_valid_bubble(g, starting_node_id):
        r"""Returns a 4-tuple of (True, a list of all the nodes in the bubble,
           the starting node in the bubble, the ending node in the bubble) if
           a bubble defined at the given start node would be valid.
           Returns a 2-tuple of (False, None) if such a bubble would be
           considered invalid.

           NOTE that we only consider "simple" bubbles that look like

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
        # The starting node in a bubble obviously must have at least 2 outgoing
        # edges. If not, we can bail early on.
        m_node_ids = list(g.adj[starting_node_id].keys())
        if len(m_node_ids) <= 1:
            return False, None

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
                return False, None

            # Ok, so this tentatively seems like a valid path.
            outgoing_node_id_from_m = list(g.adj[m].keys())[0]

            # If this is the first "middle" node we're checking, then record
            # its outgoing node as the tentative "ending" node
            if ending_node_id is None:
                ending_node_id = outgoing_node_id_from_m
            # If we've already checked another middle node, verify that this
            # middle node converges to the same "ending"
            elif ending_node_id != outgoing_node_id_from_m:
                return False, None

        # Check that the ending node is reasonable

        # If the ending node has any incoming nodes that aren't in m_node_ids,
        # reject this bubble.
        if set(g.pred[ending_node_id]) != set(m_node_ids):
            return False, None

        # Reject cyclic bubbles (although we could allow this if people want
        # it, I guess?)
        if starting_node_id in list(g.adj[ending_node_id].keys()):
            return False, None

        # Ensure that all nodes in the bubble are distinct (protects against
        # weird cases like
        #
        #   -> m1 ->
        # s -> m2 -> s
        #
        # Where the starting node is the ending node, etc.)
        composite = [starting_node_id] + m_node_ids + [ending_node_id]
        if len(set(composite)) != len(composite):
            return False, None

        # If we've gotten here, then we know that this is a valid bubble.
        return True, composite, starting_node_id, ending_node_id

    @staticmethod
    def is_valid_chain(g, starting_node_id):
        """Returns a 2-tuple of (True, a list of all the nodes in the Chain
        in order from start to end) if a Chain defined at the given start
        node would be valid. Returns a 2-tuple of (False, None) if such a
        Chain would be considered invalid.

        NOTE that this finds the longest possible Chain that includes s,
        if a Chain exists starting at s. If we decide that no Chain
        exists starting at s then we just return (False, None), but if we
        find that a Chain does exist starting at s then we traverse
        "backwards" to find the longest possible chain including s.

        ALSO NOTE that if this is actually a cyclic chain (i.e. the end node
        of the chain has an edge to the start node of the chain), we will
        return (False, None). These sorts of cases should be caught when
        looking for cyclic chains later on.

        Ideally there would be a preexisting function in NetworkX that
        computes this, but I wasn't able to find something that does this.
        If you're aware of another library's implementation of this sort of
        thing, let me know! It'd be nice to avoid duplication of effort.
        """
        out_node_ids = list(g.adj[starting_node_id].keys())
        # If the starting node doesn't have an outgoing edge to exactly one
        # node -- or even if it does, but if that node is itself -- then this
        # isn't a valid chain
        if len(out_node_ids) != 1 or out_node_ids[0] == starting_node_id:
            return False, None

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
            return False, None

        in_node_ids = list(g.pred[starting_node_id].keys())
        if len(in_node_ids) != 1:
            # We can't extend the chain "backwards" from the start,
            # so just return what we have currently. This is an "optimal" chain
            # ("optimal" in the sense that, of all possible chains that include
            # this starting node, this is the largest).
            return True, chain_list

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
                return False, None

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
            return True, chain_list

        # If we're here, we found a more optimal starting node. Nice!
        backwards_chain_list.reverse()
        return True, backwards_chain_list + chain_list

    def add_pattern(self, member_node_ids):
        """Adds a pattern composed of a list of node IDs to the decomposed
        DiGraph, and removes its children from the decomposed DiGraph.

        Routes incoming edges to nodes within this pattern (from outside of the
        pattern) to point to the pattern node, and routes outgoing edges from
        nodes within this pattern (to outside of the pattern) to originate from
        the pattern node.

        Returns the unique ID of the pattern node, which will just be an
        integer number. (This is safe b/c all of the nodes in the graph should
        have integer numbers in the range [0, # nodes - 1], so we can just set
        this pattern's ID to (# nodes).
        """
        pattern_id = self.get_new_node_id()
        # Get incoming edges to this pattern
        in_edges = self.decomposed_digraph.in_edges(member_node_ids)
        p_in_edges = list(
            filter(lambda e: e[0] not in member_node_ids, in_edges)
        )
        # Get outgoing edges from this pattern
        out_edges = self.decomposed_digraph.out_edges(member_node_ids)
        p_out_edges = list(
            filter(lambda e: e[1] not in member_node_ids, out_edges)
        )
        # Add this pattern to the decomposed digraph, with the same in/out
        # nodes as in the subgraph of this chain's nodes (and the same UUID,
        # of course)
        self.decomposed_digraph.add_node(pattern_id)
        for e in p_in_edges:
            self.decomposed_digraph.add_edge(e[0], pattern_id)
        for e in p_out_edges:
            self.decomposed_digraph.add_edge(pattern_id, e[1])

        # Remove the children of this pattern from the decomposed DiGraph
        # (they're not gone forever, of course! -- we should hold on a
        # reference to everything, albeit sort of circuitously -- so the
        # topmost pattern has a reference to its child nodes' and patterns'
        # IDs, and these child pattern(s) will have references to their
        # children node/pattern IDs, etc.)
        self.decomposed_digraph.remove_nodes_from(member_node_ids)
        return pattern_id

    def add_pattern_and_duplicate_nodes(
        self, member_node_ids, starting_node_id, ending_node_id
    ):
        """Adds a pattern composed of a list of node IDs to the decomposed
        DiGraph, and removes its children from the decomposed DiGraph.

        Additionally, this will attempt to add duplicate nodes for the starting
        and ending node IDs provided. Incoming edges to the start node will be
        routed to its new duplicate node, and outgoing edges from the ending
        node will be routed from its new duplicate node. If the starting node
        is already a duplicate, then it will not be duplicated again;
        similarly, if the ending node is already a duplicate, then it will not
        be duplicated again.

        TODO RM After the above steps, if there are any remaining edges from
        outside of the pattern incident on any of the nodes within the
        pattern, then this will raise an error: this is an indication that the
        start and ending nodes provided were inaccurate.

        This function is intended to be used with bubbles: the duplication
        process allows for "chains" of bubbles to all be detected and collapsed
        in a way that accurately models the underlying biology (i.e. we're not
        collapsing adjacent bubbles _into_ each other -- rather, we're
        collapsing adjacent bubbles independently). See #84 on GitHub for
        details.

        Returns the unique ID of the pattern.
        """
        pattern_id = self.get_new_node_id()
        self.decomposed_digraph.add_node(pattern_id)

        # Let's say we have something like:
        #
        #        2
        #       / \
        # 0 -> 1   4 -> 5
        #       \ /
        #        3
        #
        # We want to end up with:
        #
        #         +-------+
        #         |   2   |
        #         |  / \  |
        # 0 -> 6 == 1   4 == 7 -> 5
        #         |  \ /  |
        #         |   3   |
        #         +-------+

        for old_node_id in (starting_node_id, ending_node_id):
            data = self.decomposed_digraph.nodes[old_node_id]
            if "is_dup" in data and data["is_dup"]:
                # This node is already a duplicate! What this means is that
                # (if this is a starting node for the current pattern) then it
                # was previously used as the ending node for another pattern,
                # or vice versa. So, this means that we have a situation like:
                #
                #         +-------+
                #         |   2   |     8
                #         |  / \  |    / \
                # 0 -> 6 == 1   4 === 7   A -> B
                #         |  \ /  |    \ /
                #         |   3   |     9
                #         +-------+
                #
                # ... where we're currently trying to add a pattern for the
                # second bubble (starting at 7 and ending at 10). There is no
                # point in duplicating 7, since it's already the end of an
                # existing pattern. So we can just use 7 as is in a bubble:
                #
                #         +-------+ +-------+
                #         |   2   | |   8   |
                #         |  / \  | |  / \  |
                # 0 -> 6 == 1   4 === 7   A == C -> B
                #         |  \ /  | |  \ /  |
                #         |   3   | |   9   |
                #         +-------+ --------+
                #
                # Resulting in a fully collapsed thing of:
                #
                # 0 -> 6 == P1 == P2 == C -> B
                #
                # And post trimming unused duplicate nodes:
                #
                # 0 -> P1 == P2 -> B
                continue

            # Create a new node, with a new unique integer ID that picks up
            # right where the last one should've left off (if the graph has 4
            # nodes then the last integer ID should be 3; so this'll add a node
            # with the ID 4, etc.)
            new_node_id = self.get_new_node_id()
            # This new node shares all of the metadata (name, length, etc.)
            # that the original node has. This is what the ** is doing; it's
            # extracting a dict of this metadata and passing it as keywords to
            # add_node().
            self.decomposed_digraph.add_node(
                new_node_id,
                is_dup=True,
                **self.decomposed_digraph.nodes[old_node_id]
            )
            # Similarly to how we applied all of the node metadata to the
            # duplicate, apply the edge metadata to the duplicate edge(s) we
            # need to create.
            if old_node_id == starting_node_id:
                for edge in self.decomposed_digraph.in_edges(old_node_id):
                    edge_attrs = self.decomposed_digraph.edges[edge]
                    self.decomposed_digraph.add_edge(
                        edge[0], new_node_id, **edge_attrs
                    )
                # This node should have a single outgoing edge pointing to the
                # pattern node.
                self.decomposed_digraph.add_edge(
                    new_node_id, pattern_id, from_dup=True
                )
            else:
                for edge in self.decomposed_digraph.out_edges(old_node_id):
                    edge_attrs = self.decomposed_digraph.edges[edge]
                    self.decomposed_digraph.add_edge(
                        new_node_id, edge[1], **edge_attrs
                    )
                # This node should have a single incoming edge coming from the
                # pattern node.
                self.decomposed_digraph.add_edge(
                    pattern_id, new_node_id, to_dup=True
                )

        # Remove the children of this pattern from the decomposed DiGraph. This
        # includes the node(s) which have been duplicated -- their duplicates
        # will live on, to potentially be included in another pattern.
        self.decomposed_digraph.remove_nodes_from(member_node_ids)

        return pattern_id

    def hierarchically_identify_patterns(self):
        """Run all of the pattern detection algorithms above on the graph
        repeatedly until the graph has been "fully" squished into patterns.

        I imagine this will involve converting the assembly graph into a NX
        digraph such that each top-level pattern is just represented as a
        node in the graph (so that the pattern detection algorithms
        straight-up can't tell the difference between a 'pattern' and an
        actual node in the graph). We'll have to keep doing this conversion
        at each layer, I guess, but I don't think this should be *too*
        computationally expensive (knock on wood).
        """
        # We'll modify this as we go through this method
        self.decomposed_digraph = deepcopy(self.digraph)

        while True:
            # Run through all of the pattern detection methods on all of the
            # top-level nodes (or node groups) in the decomposed DiGraph.
            # Keep doing this until we get to a point where we've run every
            # pattern detection method on the graph, and nothing new has been
            # found.
            something_collapsed = False

            # You could totally switch the order of this tuple up in order to
            # change the "precedence" of pattern detection. I don't think that
            # would make a huge difference, though...?
            for collection, validator in (
                (self.chains, AssemblyGraph.is_valid_chain),
                (self.cyclic_chains, AssemblyGraph.is_valid_cyclic_chain),
                (self.bubbles, AssemblyGraph.is_valid_3node_bubble),
                (self.bubbles, AssemblyGraph.is_valid_bubble),
                (self.frayed_ropes, AssemblyGraph.is_valid_frayed_rope),
            ):
                # We sort the nodes in order to make this deterministic
                # (I doubt the extra time cost from sorting will be a big deal)
                candidate_nodes = sorted(list(self.decomposed_digraph.nodes))
                while len(candidate_nodes) > 0:
                    n = candidate_nodes[0]
                    validator_outputs = validator(self.decomposed_digraph, n)
                    pattern_valid = validator_outputs[0]
                    if pattern_valid:
                        pattern_node_ids = validator_outputs[1]

                        if len(validator_outputs) == 4:
                            # There is a start and ending node in this pattern
                            # that we want to duplicate. See issue #84 on
                            # GitHub for lots and lots of details.
                            s_id = validator_outputs[2]
                            e_id = validator_outputs[3]
                            pattern_id = self.add_pattern_and_duplicate_nodes(
                                pattern_node_ids, s_id, e_id
                            )
                        else:
                            pattern_id = self.add_pattern(pattern_node_ids)

                        collection[pattern_id] = pattern_node_ids
                        for pn in pattern_node_ids:
                            candidate_nodes.remove(pn)
                        something_collapsed = True
                    else:
                        # If the pattern wasn't invalid, we still need to
                        # remove n
                        candidate_nodes.remove(n)
            if not something_collapsed:
                # We didn't collapse anything... so we're done here! We can't
                # do any more.
                break

    def to_dot(self):
        """Debug method. Work in progress."""
        layout = "digraph {\n"
        for cc_node_ids in nx.weakly_connected_components(
            self.decomposed_digraph
        ):
            for n in cc_node_ids:
                if n in self.digraph.nodes:
                    layout += "\t{}\n".format(n)
                else:
                    # TODO: recursively describe children of this node group
                    pass
            # TODO: describe edges.

    def to_cytoscape_compatible_format(self):
        """TODO."""
