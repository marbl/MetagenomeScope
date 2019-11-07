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
        #
        # for node in self.digraph.nodes:
        #     pass

    def identify_bubbles(self):
        candidate_nodes = self.digraph.nodes
        # make collection of candidate nodes (collection of all nodes in self.digraph -- should be a deep copy, so that we don't actually modify self.digraph!)
        # make collection of candidate bubbles (initially empty) -- where each "bubble"
            # is just a list of node ids or something, nothing fancy at all
        # for every node in the graph
            # is it the start of a bubble?
            # if so, record it in a list of candidate bubbles
        # go through all candidate bubbles in descending order by num of nodes
            # If all of the nodes in the bubble are still in candidate nodes,
            # then collapse this bubble: set its child nodes' parent prop to
            # a unique bubble id (can be a uuid or a combo of node ids,
            # doesn't really matter), remove its child nodes from the
            # candidate nodes, and add a new Node representing the bubble
            # (with requisite incoming and outgoing edges matching the
            # incoming and outgoing edges of the start and end nodes of the
            # bubble, naturally) to candidate nodes
        #
        # at this point, we've collapsed all the bubbles we've can at this
        # "stage," giving preference to larger bubbles. So far this process is
        # identical to how MetagenomeScope classic worked.
        #
        # Now, what we can do is REPEAT the process. This allows for bubbles of
        # bubbles to be created!
        # If desired, we can disallow starting or ending nodes in a bubble from
        # themselves being bubbles. You can imagine this sort of thing
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
        # MgSc).
        for node in self.digraph.nodes:
            pass
