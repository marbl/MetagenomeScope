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
        # TODO extract common node/edge attrs from parse(). There are various
        # ways to do this, from elegant (e.g. create classes for each filetype
        # parser that define the expected node/edge attrs) to patchwork (just
        # return 3 things from each parsing function and from parse(), where
        # the last two things are tuples of node and edge attrs respectively).
        self.digraph = assembly_graph_parser.parse(self.filename)
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

    @staticmethod
    def is_valid_rope(digraph, starting_node_id):
        pass

    @staticmethod
    def is_valid_cyclic_chain(digraph, starting_node_id):
        pass

    @staticmethod
    def is_valid_bubble(g, starting_node_id):
        """
              m1--m2
             /      \ 
            s        e
             \      /
              \-m1-/
        """
        # The starting node in a bubble obviously must have at least 2 outgoing
        # edges. If not, we can bail early on.
        m1_node_ids = list(g.adj[starting_node_id].keys())
        if len(m1_node_ids) <= 1:
            return False, None

        # Will be recorded here (if we get to it...)
        ending_node_id = None

        # Each outgoing node from the "starting node" represents a possible
        # path through this bubble.
        for m in m1_node_ids:
            # ... And of course, each node on this path can't have extra
            # incoming nodes (which would be from outside of the bubble) or
            # extra outgoing nodes (which would represent non-bubble-like
            # branching behavior).
            if len(g.pred[m]) != 1 or len(g.adj[m]) != 1:
                return False, None
            # Check to see if we an build a "Chain" of >= 2 nodes starting at
            # m. If so, do so! (TODO: structure code so that this either
            # produces a bubble with a child chain, or structure
            # hierarchically_identify_patterns() so that chains are always
            # detected before bubbles? or just acknowledge that bottom-level
            # chains in bubbles/patterns just won't get identified)
            chain_validity, path_nodes = AssemblyGraph.is_valid_chain(g, m)
            if not chain_validity:
                # Try out single middle node case
                pass
            else:
                # Middle nodes form a chain -- great! check that this works
                pass

        # Check ending node details
        # Check entire bubble structure
        # Return stuff

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


    def hierarchically_identify_patterns(self):
        """WIP: Eventually, this will run all of the pattern detection
           algorithms above on the graph repeatedly until the graph has been
           "fully" squished into patterns.

           I imagine this will involve converting the assembly graph into a NX
           digraph such that each top-level pattern is just represented as a
           node in the graph (so that the pattern detection algorithms
           straight-up can't tell the difference between a 'pattern' and an
           actual node in the graph). We'll have to keep doing this conversion
           at each layer, I guess, but I don't think this should be *too*
           computationally expensive (knock on wood).
        """


        # make collection of candidate nodes (collection of all nodes in self.digraph -- should be a deep copy, so that we don't actually modify self.digraph!)
        candidate_nodes = list(self.digraph.nodes)
        # make collection of candidate bubbles (initially empty) -- where each "bubble"
        # is just a list of node ids or something, nothing fancy at all
        candidate_bubbles = []

        # The output: a list of identified bubbles that we can collapse in the
        # visualization
        identified_bubbles = []

        # for every node in the graph
        for n in candidate_nodes:
            # is it the start of a bubble?
            bubble_valid, bubble_node_ids = AssemblyGraph.is_valid_bubble(n)
            # if so, record it in a list of candidate bubbles
            if bubble_valid:
                # Create bubble object or list or whatever?
                candidate_bubbles.append(bubble_node_ids)

        if len(candidate_bubbles) > 0:
            pass
            # sort bubbles in descending order by num of nodes
            # go through all candidate bubbles (in descending order)
            # If all of the nodes in the bubble are still in candidate nodes,
            # then collapse this bubble: set its child nodes' parent prop to
            # a unique bubble id (can be a uuid or a combo of node ids,
            # doesn't really matter), remove its child nodes from the
            # candidate nodes, and add a new Node representing the bubble
            # (with requisite incoming and outgoing edges matching the
            # incoming and outgoing edges of the start and end nodes of the
            # bubble, naturally) to candidate nodes
            # (also, add this bubble's info to identified_bubbles)
            #
            # at this point, we've collapsed all the bubbles we've can at this
            # "stage," giving preference to larger bubbles. So far this process is
            # basically identical to how MetagenomeScope classic (tm) (just
            # kidding) worked.
            #
            # Now, what we can do is REPEAT the process. This allows for bubbles of
            # bubbles to be created!
            # If desired, we can disallow starting or ending nodes in a bubble from
            # themselves being bubbles. You can imagine that sort of thing
            # happening when you have a repeating sequence of bubbles, e.g.
            #
            #   b   e
            #  / \ / \
            # a   d   g
            #  \ / \ /
            #   c   f
            #
            # Ordinarily, this would collapse either the "ad" or "dg" bubble first
            # (arbitrary in this case since they both have 4 nodes) and then on the
            # next go-round collapse the other bubble into a superbubble involving
            # the first bubble. But if you don't want this behavior, disallowing
            # starting/ending nodes in a bubble from themselves being bubbles would
            # just collapse one bubble then stop (again, analogous to classic
            # MgSc). This limtiation is due to the way MetagenomeScope's layout
            # algorithm works -- a given node can only have one parent node
            # group (sure, it can have *grandparent* / etc. node groups, but it
            # can't be in two places at once).
        else:
            # We couldn't detect any (more) bubbles -- at this point, we're
            # done.
            # Actually, is returning this list the best thing? maybe modifying
            # stuff as we go above is clearer. whatever, it'll work out
            return identified_bubbles
