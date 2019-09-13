import networkx as nx
from .basic_objects import Node
from ..input_node_utils import gc_content, negate_node_id

# import gfapy


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
        self.digraph = None
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
        pass
        # digraph = nx.gml.read_gml(filename)
        # nodes = digraph.nodes()

    @staticmethod
    def parse_gfa(filename):
        pass
        # gfa_graph = gfapy.Gfa.from_file(filename)
        # get nodes, convert to nx digraph, ...

    @staticmethod
    def parse_fastg(filename):
        raise NotImplementedError(
            "FASTG support isn't done yet! Give me a few weeks!"
        )

    @staticmethod
    def parse_lastgraph(filename):
        """Returns a nx.DiGraph representation of a LastGraph (Velvet) file.

        As far as I'm aware, there isn't a standard LastGraph parser available
        for Python. This function, then, just uses a simple line-by-line
        parser. It's not a very smart parser, so if your LastGraph file isn't
        "standard" (e.g. has empty lines between nodes), this will get messed
        up.

        Fun fact: this parser was the first part of MetagenomeScope I ever
        wrote! (I've updated the code since to be a bit less sloppy.)

        References
        ----------
        https://www.ebi.ac.uk/~zerbino/velvet/Manual.pdf
            Includes documentation of the LastGraph file format in section
            4.2.4.

        https://github.com/rrwick/Bandage
            The behavior of the LastGraph parser here (i.e. calculating depth
            as $O_COV_SHORT_1 / $COV_SHORT_1) was primarily based on chucking
            LastGraph files into Bandage and seeing how it handled them.
        """
        digraph = nx.DiGraph()
        with open(filename, "r") as graph_file:
            parsing_node = False
            parsed_fwdseq = False
            curr_node_attrs = {
                "id": "",
                "length": -1,
                "depth": -1,
                "fwdseq": None,
                "revseq": None,
            }
            for line in graph_file:
                if line.startswith("NODE"):
                    parsing_node = True
                    line_contents = line.split()
                    curr_node_attrs["id"] = line_contents[1]
                    if curr_node_attrs["id"][0] == "-":
                        raise ValueError(
                            "Node IDs in the input assembly graph cannot "
                            'start with the "-" character.'
                        )
                    curr_node_attrs["length"] = int(line_contents[2])
                    # NOTE: we define "depth" as just the node's O_COV_SHORT_1
                    # value divided by the node's length (its COV_SHORT_1
                    # value). This decision mirrors Bandage's behavior with
                    # LastGraph files.
                    curr_node_attrs["depth"] = (
                        float(line_contents[3]) / curr_node_attrs["length"]
                    )
                elif line.startswith("ARC"):
                    line_contents = line.split()
                    id1, id2 = line_contents[1], line_contents[2]
                    nid1 = negate_node_id(line_contents[1])
                    nid2 = negate_node_id(line_contents[2])
                    multiplicity = int(line_contents[3])
                    digraph.add_edge(id1, id2, multiplicity=multiplicity)
                    # Only add implied edge if the edge does not imply itself
                    # (e.g. "ABC" -> "-ABC" or "-ABC" -> "ABC")
                    if not (id1 == nid2 and id2 == nid1):
                        digraph.add_edge(nid2, nid1, multiplicity=multiplicity)
                elif parsing_node:
                    if not parsed_fwdseq:
                        curr_node_attrs["fwdseq"] = line.strip()
                        # OK, now we've read in two lines: the first line of
                        # this node (describing general information), and the
                        # second line of this node (containing the forward
                        # sequence, a.k.a. $ENDS_OF_KMERS_OF_NODE). We can
                        # add a node for the "positive" node to the digraph.
                        digraph.add_node(
                            curr_node_attrs["id"],
                            length=curr_node_attrs["length"],
                            depth=curr_node_attrs["depth"],
                            gc_content=gc_content(curr_node_attrs["fwdseq"]),
                        )
                        parsed_fwdseq = True
                    else:
                        curr_node_attrs["revseq"] = line.strip()
                        # Now we can add a node for the "negative" node.
                        digraph.add_node
                        digraph.add_node(
                            negate_node_id(curr_node_attrs["id"]),
                            length=curr_node_attrs["length"],
                            depth=curr_node_attrs["depth"],
                            gc_content=gc_content(curr_node_attrs["revseq"]),
                        )
                        # At this point, we're done with parsing this node.
                        # Clear our temporary variables for later use if
                        # parsing other nodes.
                        parsing_node = False
                        parsed_fwdseq = False
                        curr_node_attrs = {
                            "id": "",
                            "length": -1,
                            "depth": -1,
                            "fwdseq": None,
                            "revseq": None,
                        }
        return digraph

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

        # TODO convert the digraph into a collection of Node/Edge objects (i.e.
        # populate the current class).
        # Then we can just continue with the preprocessing script as normal
        # (pattern detection, layout, ...)
