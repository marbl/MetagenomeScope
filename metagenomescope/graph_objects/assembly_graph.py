import math
from copy import deepcopy
import numpy
import networkx as nx
from .. import assembly_graph_parser, config
from .pattern import StartEndPattern, Pattern


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

        # Each entry in these structures will be a Pattern (or subclass).
        # NOTE that these patterns will only be "represented" in
        # self.decomposed_digraph; self.digraph represents the literal graph
        # structure as initially parsed (albeit with some duplicate nodes added
        # in for convenience's sake, maybe).
        self.chains = []
        self.cyclic_chains = []
        self.bubbles = []
        self.frayed_ropes = []

        self.id2pattern = {}

        # TODO extract common node/edge attrs from parse(). There are various
        # ways to do this, from elegant (e.g. create classes for each filetype
        # parser that define the expected node/edge attrs) to patchwork (just
        # return 3 things from each parsing function and from parse(), where
        # the last two things are tuples of node and edge attrs respectively).
        # Eventually we'll need to check for conflicting attribute names (e.g.
        # relative_length, longside_proportion, etc.) Maybe reserve _mgsc as
        # proportion prefix?
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

    def get_edge_weight_field(self, field_names=["bsize", "multiplicity"]):
        """Returns the name of the edge weight field this graph has.

        If the graph does not have any edge weight fields, returns None.

        The list of field names corresponding to "edge weights" is
        configurable via the field_names parameter. The two fields accepted
        now (bsize and multiplicity) are both verified in the assembly graph
        parser to correspond to positive integers, so future fields accepted
        as edge weights should also be verified in this way.

        NOTE that this assumes that at least one edge having a weight
        implies that the other edges in the graph have weights. This should
        always be the case, but if there are graphs with partial edge weight
        data then this may cause problems with scaling later on.
        """
        fn_had = None
        for fn in field_names:
            if len(nx.get_edge_attributes(self.digraph, fn)) > 0:
                if fn_had is None:
                    fn_had = fn
                else:
                    raise ValueError(
                        (
                            "Graph has multiple 'edge weight' fields, "
                            "including {} and {}. It's ambiguous which we "
                            "should use for scaling."
                        ).format(fn_had, fn)
                    )
        return fn_had

    def has_edge_weights(self):
        """Returns True if the graph has edge weight data, False otherwise."""
        return self.get_edge_weight_field() is not None

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
    def is_bubble_boundary_node_invalid(g, node_id):
        """Returns True if the node is a collapsed pattern that is NOT a
        bubble, False otherwise.

        Basically, the purpose of this is rejecting things like frayed
        ropes that don't make sense as the start / end nodes of bubbles.
        """
        if "pattern_type" in g.nodes[node_id]:
            return g.nodes[node_id]["pattern_type"] != "bubble"
        return False

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
        # Starting node must be either an uncollapsed node or another bubble
        if AssemblyGraph.is_bubble_boundary_node_invalid(g, starting_node_id):
            return False, None

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

        # Verify that end node is either an uncollapsed node or another bubble
        if AssemblyGraph.is_bubble_boundary_node_invalid(g, e):
            return False, None

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

        # For now, bubbles can only start with 1) uncollapsed nodes or 2) other
        # bubbles (which'll cause us to duplicate stuff)
        if AssemblyGraph.is_bubble_boundary_node_invalid(g, starting_node_id):
            return False, None

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

        # If the ending node is a non-bubble pattern, reject this (for now).
        if AssemblyGraph.is_bubble_boundary_node_invalid(g, ending_node_id):
            return False, None

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

    def add_pattern(self, member_node_ids, pattern_type):
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
        # nodes as in the subgraph of this pattern's nodes
        self.decomposed_digraph.add_node(
            pattern_id, pattern_type=pattern_type, children=member_node_ids
        )
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

        p = Pattern(pattern_id, pattern_type, member_node_ids)
        return p

    def add_bubble(self, member_node_ids, starting_node_id, ending_node_id):
        """Adds a bubble composed of a list of node IDs to the decomposed
        DiGraph, and removes its children from the decomposed DiGraph.

        Additionally, this will check to see if the nodes corresponding to
        starting_node_id and ending_node_id are themselves collapsed patterns
        (for now they can only be other bubbles, but in theory any pattern with
        a single starting and end node is kosher -- e.g. chains, cyclic
        chains).

        If the starting node is already a collapsed pattern, this will
        duplicate the ending node of that pattern within this new bubble and
        create a link accordingly. Similarly, if the ending node is already a
        collapsed pattern, this'll duplicate the starting node of that bubble
        in the new bubble.

        Returns the unique ID of the bubble.
        """
        pattern_id = self.get_new_node_id()
        self.decomposed_digraph.add_node(
            pattern_id, pattern_type="bubble", children=member_node_ids
        )

        if "pattern_type" in self.decomposed_digraph.nodes[starting_node_id]:
            # In the decomposed digraph, link the starting pattern with the
            # curr pattern.
            self.decomposed_digraph.add_edge(
                starting_node_id, pattern_id, is_dup=True
            )
            # In the actual digraph, create a new node that'll serve as the
            # "duplicate" of this node within the new pattern we're creating.
            # Shares all data, and holds the outgoing edges of the original
            # node -- all of these outgoing edges should be _within_ this new
            # pattern.

            # Get ending node of the starting pattern, and duplicate it
            end_node_to_dup = self.id2pattern[starting_node_id].get_end_node()
            data = self.digraph.nodes[end_node_to_dup]
            new_node_id = self.get_new_node_id()
            self.digraph.add_node(new_node_id, is_dup=True, **data)

            # Duplicate outgoing edges of the duplicated node
            for edge in list(self.digraph.out_edges(end_node_to_dup)):
                edge_data = self.digraph.edges[edge]
                self.digraph.add_edge(new_node_id, edge[1], **edge_data)
                self.digraph.remove_edge(end_node_to_dup, edge[1])

            self.digraph.add_edge(end_node_to_dup, new_node_id, is_dup=True)

            member_node_ids.remove(starting_node_id)
            member_node_ids.append(new_node_id)
            starting_node_id = new_node_id

        if "pattern_type" in self.decomposed_digraph.nodes[ending_node_id]:
            self.decomposed_digraph.add_edge(
                pattern_id, ending_node_id, is_dup=True
            )
            # Get starting node of the ending pattern, and duplicate it
            start_node_to_dup = self.id2pattern[
                ending_node_id
            ].get_start_node()
            data = self.digraph.nodes[start_node_to_dup]
            new_node_id = self.get_new_node_id()
            self.digraph.add_node(new_node_id, is_dup=True, **data)

            # Duplicate incoming edges of the duplicated node
            for edge in list(self.digraph.in_edges(start_node_to_dup)):
                edge_data = self.digraph.edges[edge]
                self.digraph.add_edge(edge[0], new_node_id, **edge_data)
                self.digraph.remove_edge(edge[0], start_node_to_dup)

            self.digraph.add_edge(new_node_id, start_node_to_dup, is_dup=True)

            member_node_ids.remove(ending_node_id)
            member_node_ids.append(new_node_id)
            ending_node_id = new_node_id

        # NOTE TODO abstract between this and prev func.
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
        for e in p_in_edges:
            self.decomposed_digraph.add_edge(e[0], pattern_id)
        for e in p_out_edges:
            self.decomposed_digraph.add_edge(pattern_id, e[1])

        # Remove the children of this pattern from the decomposed DiGraph.
        self.decomposed_digraph.remove_nodes_from(member_node_ids)

        p = StartEndPattern(
            pattern_id,
            "bubble",
            member_node_ids,
            starting_node_id,
            ending_node_id,
        )
        return p

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
            for collection, validator, ptype in (
                (self.chains, AssemblyGraph.is_valid_chain, "chain"),
                (
                    self.cyclic_chains,
                    AssemblyGraph.is_valid_cyclic_chain,
                    "cyclicchain",
                ),
                (self.bubbles, AssemblyGraph.is_valid_3node_bubble, "bubble"),
                (self.bubbles, AssemblyGraph.is_valid_bubble, "bubble"),
                (
                    self.frayed_ropes,
                    AssemblyGraph.is_valid_frayed_rope,
                    "frayedrope",
                ),
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

                        if ptype == "bubble":
                            # There is a start and ending node in this pattern
                            # that we may want to duplicate. See issue #84 on
                            # GitHub for lots and lots of details.
                            s_id = validator_outputs[2]
                            e_id = validator_outputs[3]
                            p = self.add_bubble(pattern_node_ids, s_id, e_id)
                        else:
                            p = self.add_pattern(pattern_node_ids, ptype)

                        collection.append(p)
                        candidate_nodes.append(p.pattern_id)
                        self.id2pattern[p.pattern_id] = p
                        for pn in p.node_ids:
                            # Remove nodes if they're in candidate nodes. There
                            # may be nodes in this pattern not in candidate
                            # nodes, e.g. if duplication was done. In that case
                            # no need to do anything for those nodes.
                            # This should perform decently; see
                            # https://stackoverflow.com/a/4915964/10730311.
                            try:
                                candidate_nodes.remove(pn)
                            except ValueError:
                                continue
                        something_collapsed = True
                    else:
                        # If the pattern wasn't invalid, we still need to
                        # remove n
                        candidate_nodes.remove(n)
            if not something_collapsed:
                # We didn't collapse anything... so we're done here! We can't
                # do any more.
                break

    def layout(self):
        """Lays out the graph. ...This part is important!"""
        # For each component:
        # -Identify patterns in the component. Lay out these patterns. If these
        #  patterns contain other patterns, lay out those patterns first (this
        #  is recursive since there can be many layers of patterns), and then
        #  use the pattern bounding box for backfilling.
        # -Finally, lay out the entire component.
        # -Backfill all node/edge coordinates within patterns in. This will
        #  need to also be recursive to accommodate really deep down stuff.

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

    def scale_nodes(self):
        """Scales nodes in the graph based on their lengths.

        This assigns two new attributes for each node:

        1. relative_length: a number in the range [0, 1]. Corresponds to
           where log(node length) falls in a range between log(min node
           length) and log(max node length), relative to the rest of the
           graph's nodes. Used for scaling node area.

        2. longside_proportion: another number in the range [0, 1], assigned
           based on the relative percentile range the node's log length
           falls into. Used for determining the proportions of a node, and
           how "long" it looks.

        Previously, this scaled nodes in separate components differently.
        However, MetagenomeScope will (soon) be able to show multiple
        components at once, so we scale nodes based on the min/max lengths
        throughout the entire graph.
        """
        node_lengths = nx.get_node_attributes(self.digraph, "length")
        node_log_lengths = {}
        for node, length in node_lengths.items():
            node_log_lengths[node] = math.log(
                length, config.CONTIG_SCALING_LOG_BASE
            )
        min_log_len = min(node_log_lengths.values())
        max_log_len = max(node_log_lengths.values())
        if min_log_len == max_log_len:
            for node in self.digraph.nodes:
                self.digraph.nodes[node]["relative_length"] = 0.5
                self.digraph.nodes[node][
                    "longside_proportion"
                ] = config.MID_LONGSIDE_PROPORTION
        else:
            log_len_range = max_log_len - min_log_len
            q25, q75 = numpy.percentile(
                list(node_log_lengths.values()), [25, 75]
            )
            for node in self.digraph.nodes:
                node_log_len = node_log_lengths[node]
                self.digraph.nodes[node]["relative_length"] = (
                    node_log_len - min_log_len
                ) / log_len_range
                if node_log_len < q25:
                    lp = config.LOW_LONGSIDE_PROPORTION
                elif node_log_len < q75:
                    lp = config.MID_LONGSIDE_PROPORTION
                else:
                    lp = config.HIGH_LONGSIDE_PROPORTION
                self.digraph.nodes[node]["longside_proportion"] = lp

    def scale_edges(self):
        """Scales edges in the graph based on their weights, if present.

        If this graph has edge weights, this assigns two new attributes for
        each edge:

        1. is_outlier: one of -1, 0, or 1. Ways to interpret this:
            -1: This edge's weight is a low outlier
             0: This edge's weight is not an outlier
             1: This edge's weight is a high outlier

           NOTE that if the graph has less than 4 edges, this'll just set all
           of their is_outlier values to 0 (since with such a small number of
           data points the notion of "outliers" kinda breaks apart).

        2. relative_weight: a number in the range [0, 1]. If this edge is not
           an outlier, this corresponds to where this edge's weight falls
           within a range between the minimum non-outlier edge weight and the
           maximum non-outlier edge weight. If this edge is a low outlier, this
           will just be 0, and if this edge is a high outlier, this will just
           be 1.

        If edge weight scaling cannot be done for some or all edges
        (e.g. no edge weight data is available, or only one non-outlier edge
        exists) then this will assign is_outlier = 0 and relative_weight = 0.5
        to the impacted edges.

        Relative scaling will only be done for non-outlier edges. This helps
        make things look more consistent.

        Outlier detection is done using "inner" Tukey fences, as described in
        Exploratory Data Analysis (1977).
        """

        def _assign_default_weight_attrs(edges):
            """Assigns "normal" attributes to each edge in edges."""
            for edge in edges:
                self.digraph.edges[edge]["is_outlier"] = 0
                self.digraph.edges[edge]["relative_weight"] = 0.5

        ew_field = self.get_edge_weight_field()
        if ew_field is not None:
            real_edges = []
            weights = []
            fake_edges = []
            for edge in self.digraph.edges:
                data = self.digraph.edges[edge]
                if "is_dup" not in data:
                    real_edges.append(edge)
                    weights.append(data[ew_field])
                else:
                    fake_edges.append(edge)

            non_outlier_edges = []
            non_outlier_edge_weights = []
            # Only try to flag outlier edges if the graph contains at least 4
            # edges. With < 4 data points, computing quartiles becomes a bit
            # silly.
            if len(weights) >= 4:
                # Calculate lower and upper Tukey fences. First, compute the
                # upper and lower quartiles (aka the 25th and 75th percentiles)
                lq, uq = numpy.percentile(weights, [25, 75])
                # Determine 1.5 * the interquartile range.
                # (If desired, we could use other values besides 1.5 -- this
                # isn't set in stone.)
                d = 1.5 * (uq - lq)
                # Now we can calculate the actual Tukey fences:
                lf = lq - d
                uf = uq + d
                # Now, iterate through every edge and flag outliers.
                # Non-outlier edges will be added to a list of edges that we'll
                # scale relatively.
                for edge in real_edges:
                    data = self.digraph.edges[edge]
                    ew = data[ew_field]
                    if ew > uf:
                        data["is_outlier"] = 1
                        data["relative_weight"] = 1
                    elif ew < lf:
                        data["is_outlier"] = -1
                        data["relative_weight"] = 0
                    else:
                        data["is_outlier"] = 0
                        non_outlier_edges.append(edge)
                        non_outlier_edge_weights.append(ew)
            else:
                # There are < 4 edges, so consider all edges as "non-outliers."
                for edge in real_edges:
                    data = self.digraph.edges[edge]
                    if "is_dup" not in data:
                        data["is_outlier"] = 0
                        non_outlier_edges.append(edge)
                        ew = data[ew_field]
                        non_outlier_edge_weights.append(ew)

            # Perform relative scaling for non-outlier edges, if possible.
            if len(non_outlier_edges) >= 2:
                min_ew = min(non_outlier_edge_weights)
                max_ew = max(non_outlier_edge_weights)
                if min_ew != max_ew:
                    ew_range = max_ew - min_ew
                    for edge in non_outlier_edges:
                        data = self.digraph.edges[edge]
                        ew = data[ew_field]
                        rw = (ew - min_ew) / ew_range
                        data["relative_weight"] = rw
                else:
                    # Can't do edge scaling, so just assign this list of edges
                    # (... which should in practice just be a list with one or
                    # zero edges, I guess...?) "default" edge weight attributes
                    _assign_default_weight_attrs(non_outlier_edges)
            # Assign default edge weight attrs to fake edges, i.e. those
            # between a node and its duplicate
            _assign_default_weight_attrs(fake_edges)
        else:
            # Can't do edge scaling, so just assign every edge "default" attrs
            _assign_default_weight_attrs(self.digraph.edges)
