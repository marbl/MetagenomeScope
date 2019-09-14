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
        self.digraph = assembly_graph_parser.parse(self.filename)
        # Convert self.digraph into collections of Node/Edge objects.
        for node in self.digraph.nodes:
            pass
