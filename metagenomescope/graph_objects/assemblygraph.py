import networkx as nx
import gfapy

class AssemblyGraph(object):
    """Representation of an input assembly graph.

       This contains information about the top-level structure of the graph:
       including nodes, edges, and connected components.

       In fancy object-oriented programming terminology, this class is a
       "composition" with a NetworkX DiGraph. This really just means that,
       rather than subclassing nx.DiGraph, this class just contains an instance
       of nx.DiGraph (self.digraph) that we occasionally delegate to.

       CODELINK: This paradigm was implemented based on this post:
       https://www.thedigitalcatonline.com/blog/2014/08/20/python-3-oop-part-3-delegation-composition-and-inheritance/
    """

    def __init__(self, filename):
        """Initializes the AssemblyGraph object as an empty graph.

           This does *not* parse the graph located at filename -- you'll need
           to call .parse() to do that, which will populate this graph with
           nodes and edges.
        """
        self.filename = filename
        self.digraph = nx.DiGraph()
        self.nodes = []
        self.edges = []
        self.components = []


    def _sniff_filetype(self):
        """Attempts to determine the filetype of the file specified by
           self.filename.

           Currently, this just returns the extension of the filename (after
           converting the filename to lowercase). If the extension isn't one of
           "lastgraph", "gfa", "fastg", or "gml", this throws an error.
           this fails.
        """
        lowercase_fn = self.filename.lower()
        supported_filetypes = ("lastgraph", "gfa", "fastg", "gml")
        for suffix in supported_filetypes:
            if lowercase_fn.endswith(suffix):
                return suffix
        raise NotImplementedError(
            "The input filename ({}) doesn't end with one of the following "
            "supported filetypes: {}. Please provide an assembly graph that "
            "follows one of these filetypes and is named accordingly.".format(
                self.filename, supported_filetypes
            )
        )

    @staticmethod
    def parse_gml(filename):
        digraph = nx.gml.read_gml(filename)
        nodes = digraph.nodes()


    @staticmethod
    def parse_gfa(filename):
        gfa_graph = gfapy.Gfa.from_file(filename)
        # get nodes, convert to nx digraph, ...

    @staticmethod
    def parse_fastg(filename):
        raise NotImplementedError(
            "FASTG support isn't done yet! Give me a few weeks!"
        )

    @staticmethod
    def parse_lastgraph(filename):
        # gotta do this line by line, i guess
        # .. build up nx digraph, etc
        pass

    def parse(self):
        putative_filetype = self._sniff_filetype()

        if putative_filetype == "gml":
            self.digraph = AssemblyGraph.parse_gml(self.filename)

        elif putative_filetype == "gfa":
            self.digraph = AssemblyGraph.parse_gfa(self.filename)

        elif putative_filetype == "fastg":
            self.digraph = AssemblyGraph.parse_fastg(self.filename)

        elif putative_filetype == "LastGraph":
            self.digraph = AssemblyGraph.parse_lastgraph(self.filename)

        else:
            raise NotImplementedError(
                "Unknown filetype ({}) identified for assembly "
                "graph parsing.".format(putative_filetype)
            )
