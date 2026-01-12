import math
import os
import random
import logging
import subprocess
from copy import deepcopy
from collections import deque, defaultdict
import numpy
import networkx as nx
import pygraphviz
from .. import (
    parsers,
    config,
    cy_config,
    ui_config,
    layout_utils,
    color_utils,
    ui_utils,
    seq_utils,
    path_utils,
    name_utils,
    misc_utils,
)
from ..errors import GraphParsingError, GraphError, WeirdError
from . import validators, graph_utils
from .draw_results import DrawResults
from .component import Component
from .pattern import Pattern
from .node import Node
from .edge import Edge


# a lot of this code still relies on the old logging system. i want to
# add stuff back piece by piece, so for now here are clunky placeholder
# functions to prevent flake8 errors -- gradually i will remove references
# to these functions in favor of just using the new logging stuff
def operation_msg(*args):
    print("TEMP OM", args)


def conclude_msg(*args):
    print("TEMP CM", args)


class AssemblyGraph(object):
    """Representation of an assembly graph.

    In fancy object-oriented programming terminology, this class is a
    "composition" with a NetworkX MultiDiGraph. This really just means that,
    rather than subclassing nx.MultiDiGraph, this class just contains two
    main instances of nx.MultiDiGraph (.graph and .decomposed_graph) of which
    which we make use.

    The .graph object describes the input assembly graph structure. As we split
    the boundary nodes of certain patterns (replacing a node N with the "fake
    edge" N-L ==> N-R), we will update the .graph object to add in the new node
    and edge. However, the .graph object will only include nodes and edges --
    it will not include pattern nodes. The .graph object, after decomposition
    is done, thus represents the "original" / "fully uncollapsed" graph.

    The .decomposed_graph object describes the "top-level" / "fully collapsed"
    assembly graph structure. As we identify patterns in the graph, we will
    remove these nodes and edges from the .decomposed_graph object, replacing
    them with their parent pattern node.

    (Or, phrased differently: if you recursively replace all pattern nodes in
    the decomposed graph with their child nodes and edges, then the resulting
    graph should be equivalent to the uncollapsed graph stored in .graph.)

    References
    ----------
    CODELINK: This "composition" paradigm was based on this post:
    https://www.thedigitalcatonline.com/blog/2014/08/20/python-3-oop-part-3-delegation-composition-and-inheritance/
    """

    def __init__(
        self,
        graph_fp,
        agp_fp=None,
        flye_info_fp=None,
    ):
        """Parses the input graph file and initializes the AssemblyGraph.

        After you create a graph, you should usually call the layout() method
        to assign coordinates to nodes and edges in the graph.

        Parameters
        ----------
        graph_fp: str
            Path to the assembly graph to be visualized.

        agp_fp: str or None
            If specified, this should be a path to an AGP file describing paths
            in the graph.

        flye_info_fp: str or None
            If specified, this should be a path to a Flye assembly_info.txt
            file describing contigs/scaffolds in the graph.

        References
        ----------
        For details about AGP files, see
        https://www.ncbi.nlm.nih.gov/genbank/genome_agp_specification/

        For details about the Flye info files, see
        https://github.com/mikolmogorov/Flye/blob/flye/docs/USAGE.md
        """
        logger = logging.getLogger(__name__)

        self.filename = graph_fp
        self.basename = misc_utils.get_basename_if_fp(graph_fp)
        self.agp_filename = agp_fp
        self.agp_basename = misc_utils.get_basename_if_fp(agp_fp)
        self.flye_info_filename = flye_info_fp
        self.flye_info_basename = misc_utils.get_basename_if_fp(flye_info_fp)

        logger.info(f'Loading input graph "{self.basename}"...')
        self.filetype = parsers.FILETYPE2HR[
            parsers.sniff_filetype(self.filename)
        ]

        graph_paths = None
        parser_output = parsers.parse(self.filename)
        if self.filetype != "GFA":
            self.graph = parser_output
        else:
            self.graph = parser_output[0]
            graph_paths = parser_output[1]

        self.orientation_in_name = parsers.HRFILETYPE2ORIENTATION_IN_NAME[
            self.filetype
        ]
        self.node_centric = parsers.HRFILETYPE2NODECENTRIC[self.filetype]
        if self.node_centric:
            self.seq_noun = "node"
        else:
            self.seq_noun = "edge"
        logger.info(f'...Loaded graph. Filetype: "{self.filetype}".')

        if self.filetype != "DOT" and self.flye_info_filename is not None:
            logging.warning(
                "Flye assembly info file provided. Since the input graph "
                "is not a DOT file, we are ignoring the info file."
            )

        # These are the "raw" counts, before adding split nodes / fake edges
        # / etc during decomposition
        self.node_ct = len(self.graph.nodes)
        self.edge_ct = len(self.graph.edges)

        logger.info(
            f"Graph contains {self.node_ct:,} node(s) and {self.edge_ct:,} "
            "edge(s)."
        )
        graph_utils.validate_nonempty(self)

        logger.info("Processing the graph to prep for visualization...")

        # These store Node, Edge, and Pattern objects. We still use the
        # NetworkX graph objects to do things like identify connected
        # components, find all edges incident on a node, etc., but data about
        # these objects (both user-provided [e.g. "length"] and internal [e.g.
        # "width"] data) will primarily be stored in these objects.
        self.nodeid2obj = {}
        self.edgeid2obj = {}
        self.pattid2obj = {}

        # "Extra" data for nodes / edges -- e.g. length, GC content, coverage,
        # multiplicity, ... -- will be updated based on what we see in
        # self._init_graph_objs().
        self.extra_node_attrs = set()
        self.extra_edge_attrs = set()

        # Number of nodes, edges, and patterns in the graph, including things
        # like fake edges and split nodes. This number is used when generating
        # new unique node IDs.
        self.num_objs = 0

        # Populate self.nodeid2obj and self.edgeid2obj, re-label nodes in
        # the graph, and add an "uid" attribute for edges in the graph. This
        # way, we can easily associate nodes and edges with their corresponding
        # objects' unique IDs. (Also do some sanity checking about the graph.)
        logger.debug("  Initializing node and edge graph objects...")
        self._init_graph_objs()
        logger.debug("  ...Done.")

        logger.debug(
            f"  Computing some stats about {self.seq_noun} sequence lengths..."
        )
        self.n50 = seq_utils.n50(self.seq_lengths)
        self.total_seq_len = sum(self.seq_lengths)
        logger.debug(f"  ...Done. N50 is {self.n50:,} bp.")

        # Records the bounding boxes of each component in the graph. Indexed by
        # component number (1-indexed). (... We could also store this as an
        # array, but due to the whole component skipping stuff that sounds like
        # asking for trouble. Plus it's not like this will take up a ton of
        # memory, I think.)
        self.cc_num_to_bb = {}

        # Each entry in these structures will be a Pattern (or subclass).
        # NOTE that these patterns will only be "represented" in
        # self.decomposed_graph; self.graph represents the literal graph
        # structure as initially parsed (albeit with some split nodes added
        # in for convenience's sake, maybe).
        # NOTE 2: do we need to keep these lists around? Couldn't we just save
        # the numbers of each type of pattern? (We don't even need to do that
        # -- we could just traverse self.pattid2obj to figure it out -- but
        # storing the numbers here would save us some time.)
        self.bubbles = []
        self.chains = []
        self.cyclic_chains = []
        self.frayed_ropes = []
        self.bipartites = []
        self.ptype2collection = {
            config.PT_BUBBLE: self.bubbles,
            config.PT_CHAIN: self.chains,
            config.PT_CYCLICCHAIN: self.cyclic_chains,
            config.PT_FRAYEDROPE: self.frayed_ropes,
            config.PT_BIPARTITE: self.bipartites,
        }

        logger.debug("  Decomposing the assembly graph...")
        logger.debug("    Creating a copy of the graph...")
        self.decomposed_graph = deepcopy(self.graph)
        logger.debug("    ...Done.")

        logger.debug("    Hierarchically identifying patterns in the graph...")
        self._hierarchically_identify_patterns()
        logger.debug(
            "    ...Done. Found "
            f"{ui_utils.pluralize(len(self.bubbles), 'bubble')}, "
            f"{ui_utils.pluralize(len(self.chains), 'chain')}, "
            f"{ui_utils.pluralize(len(self.cyclic_chains), 'cyclic chain')}, "
            f"{ui_utils.pluralize(len(self.frayed_ropes), 'frayed rope')}, and "
            f"{ui_utils.pluralize(len(self.bipartites), 'bipartite')}."
        )
        logger.debug("  ...Done.")

        # Initialize self.components, a sorted list of Component objects. See
        # this method's docstring for details.
        logger.debug("  Recording information about the graph's components...")
        self._record_connected_components()
        logger.debug(
            "  ...Done. The graph has "
            f"{ui_utils.pluralize(len(self.components), 'component')}."
        )

        # To make various lookup operations (e.g. searching) easier, just map
        # node names to lists of objects as well. A nonsplit node is mapped to
        # a list containing just one Node object; a split node (e.g. "40-L")
        # is mapped to a list containing just this Node object; and the
        # basename of a split node (e.g. "40") is mapped to a list containing
        # both its split Node objects, for convenience's sake.
        logger.debug("  Creating a node name mapping for later use...")
        self.nodename2objs = defaultdict(list)
        for n in self.nodeid2obj.values():
            self.nodename2objs[n.name].append(n)
            if n.is_split():
                self.nodename2objs[n.basename].append(n)
        logger.debug("  ...Done.")

        # Process paths, if given.
        #
        # Maps path names -> list of node or edge names in path
        # (whether we think these are nodes or edges is determined by
        # self.node_centric)
        self.pathname2objnames = {}
        # Other mappings that are useful for determining available paths, etc.
        # This is kind of inelegant but whatever
        self.ccnum2pathnames = None
        self.pathname2ccnum = None
        self.objname2pathnames = None

        input_paths = {}

        # process the paths, if given
        if graph_paths is not None:
            logger.debug(
                f"  Detected {ui_utils.pluralize(len(graph_paths), 'path')} "
                f"in the input {self.filetype} file."
            )
            input_paths = graph_paths

        if self.agp_filename is not None:
            logger.debug(f'  Loading input AGP file "{self.agp_basename}"...')
            agp_paths = path_utils.get_paths_from_agp(
                self.agp_filename, self.orientation_in_name
            )
            logger.debug(
                "  ...Done. It contained "
                f"{ui_utils.pluralize(len(agp_paths), 'path')}."
            )
            path_utils.merge_paths(input_paths, agp_paths)

        if self.flye_info_filename is not None and self.filetype == "DOT":
            logger.debug(
                f'  Loading input Flye info file "{self.flye_info_basename}"'
                "..."
            )
            fi_paths = path_utils.get_paths_from_flye_info(
                self.flye_info_filename
            )
            noun = (
                "contigs/scaffolds"
                if len(fi_paths) != 1
                else "contig/scaffold"
            )
            logger.debug(f"  ...Done. It contained {len(fi_paths):,} {noun}.")
            path_utils.merge_paths(input_paths, fi_paths)

        # If there were any paths at all, record info about them (and filter
        # out paths containing stuff not in the graph)
        if len(input_paths) > 0:
            logger.debug("  Matching up paths to the graph...")
            # TODO can update path lookup stuff to use nodename2objs - faster
            id2obj = self.nodeid2obj if self.node_centric else self.edgeid2obj
            (
                self.ccnum2pathnames,
                self.objname2pathnames,
                self.pathname2ccnum,
            ) = path_utils.get_path_maps(
                id2obj, input_paths, self.node_centric
            )
            # Filter to just the paths that were available in the graph.
            for p in self.pathname2ccnum:
                self.pathname2objnames[p] = input_paths[p]
            logger.debug(
                "  ...Done. Found "
                f"{ui_utils.pluralize(len(self.pathname2objnames), 'path')} "
                "across "
                f"{ui_utils.pluralize(len(self.ccnum2pathnames), 'component')}."
            )

        # Since layout can take a while, we leave it to the creator of this
        # object to call .layout() (if for example they don't actually need to
        # lay out the graph, and they just want to do pattern detection).
        #
        # Some functions require that layout has already been performed,
        # though. These functions can just use this flag to figure out if they
        # should immediately fail with an error.
        self.layout_done = False
        logger.info("...Done.")

    def _init_graph_objs(self):
        """Initializes Node and Edge objects for the original graph.

        This clears the NetworkX data stored for each node and edge in the
        graph (don't worry, this data isn't lost -- it's saved in the
        corresponding Node and Edge objects' .data attributes). Information
        about which of these data fields are specified for the nodes/edges is
        stored in the .extra_node_attrs and .extra_edge_attrs collections.

        Also sanity checks node names.

        Also populates self.seq_lengths with the observed Node or Edge sequence
        lengths, depending on if self.node_centric is True or False.

        And assigns each node and edge a random integer in the range
        [0, |cy_config.RANDOM_COLORS| - 1]. This makes it simpler to assign
        consistent random colors later on (also, it makes it simpler to ensure
        that +/- copies of nodes/edges have the same or similar random colors).

        Finally, this relabels nodes in the graph to match their corresponding
        Node object's unique_id; and adds an "uid" attribute to edges' NetworkX
        data that matches their corresponding Edge object's unique_id.

        Raises
        ------
        WeirdError
            If not all Nodes or Edges (for a given definition of
            self.node_centric) have a defined length. This should already have
            been validated by the graph parser, so we should never encounter
            this situation. (I mean EVENTUALLY we could support graphs without
            defined lengths but that doesn't really sound all that useful...?)

        GraphParsingError
            If any of the node name sanity checking fails.

        Notes
        -----
        We may add more Node and Edge objects as we perform pattern detection
        and node splitting. That will be done separately; this method just
        establishes a "baseline."
        """
        # Ensure consistent random color choices
        random.seed(333)

        rand_idx_generator = color_utils.get_rand_idx(
            len(cy_config.RANDOM_COLORS)
        )

        extra_node_attrs_with_atleastone_entry = set()
        extra_edge_attrs_with_atleastone_entry = set()

        oldid2uniqueid = {}
        self.seq_lengths = []
        lengths_completely_defined = True
        for node_name in self.graph.nodes:
            str_node_name = str(node_name)
            name_utils.sanity_check_node_name(str_node_name)
            node_id = self._get_unique_id()
            data = deepcopy(self.graph.nodes[node_name])
            new_node = Node(node_id, str_node_name, data)
            self.nodeid2obj[node_id] = new_node

            self.extra_node_attrs |= set(data.keys())
            for a in self.extra_node_attrs:
                if a in data and data[a] is not None:
                    extra_node_attrs_with_atleastone_entry.add(a)

            # Remove node data from the graph (we've already saved it in the
            # Node object's .data attribute).
            self.graph.nodes[node_name].clear()
            # We'll re-label nodes in the graph, to make it easy to associate
            # them with their corresponding Node objects. (Don't worry -- we
            # already passed str_node_name to the corresponding Node object for
            # this node, so the user will still see it in the visualization.)
            oldid2uniqueid[node_name] = node_id

            if lengths_completely_defined and self.node_centric:
                if "length" in data:
                    self.seq_lengths.append(data["length"])
                else:
                    # at least one node doesn't have a length given, bail out
                    lengths_completely_defined = False

            # If we've already seen the RC of this node, then we'll just copy
            # its random index to this node (in order to assign it the same
            # random color as its RC).
            #
            # If we have not seen the RC of this node yet (or if that RC does
            # not exist in this graph at all), then assign this node a new
            # random index for coloring.
            rc_name = name_utils.negate(str_node_name)
            if rc_name in oldid2uniqueid:
                new_node.rand_idx = self.nodeid2obj[
                    oldid2uniqueid[rc_name]
                ].rand_idx
            else:
                new_node.rand_idx = next(rand_idx_generator)

        nx.relabel_nodes(self.graph, oldid2uniqueid, copy=False)

        edgenamepair2rand_idx = {}

        for e in self.graph.edges(data=True, keys=True):
            edge_id = self._get_unique_id()
            # e is a 4-tuple of (source ID, sink ID, key, data dict)
            data = deepcopy(e[3])
            new_edge = Edge(edge_id, e[0], e[1], data)
            self.edgeid2obj[edge_id] = new_edge

            self.extra_edge_attrs |= set(data.keys())
            for a in self.extra_edge_attrs:
                if a in data and data[a] is not None:
                    extra_edge_attrs_with_atleastone_entry.add(a)

            # Remove edge data from the graph.
            self.graph.edges[e[0], e[1], e[2]].clear()
            # Edges in NetworkX don't really have "IDs," but we can use the
            # (now-cleared) data dict in the graph to store their ID. This will
            # make it easy to associate this edge with its Edge object.
            self.graph.edges[e[0], e[1], e[2]]["uid"] = edge_id

            if lengths_completely_defined and not self.node_centric:
                if "length" in data:
                    self.seq_lengths.append(data["length"])
                elif "approx_length" in data:
                    # for flye graphs that write edge lengths as e.g. "720k"
                    self.seq_lengths.append(data["approx_length"])
                else:
                    # at least one edge doesn't have a length given, bail out
                    lengths_completely_defined = False

            src = self.nodeid2obj[e[0]]
            tgt = self.nodeid2obj[e[1]]
            namepair = (src.name, tgt.name)
            rcnamepair = (
                name_utils.negate(tgt.name),
                name_utils.negate(src.name),
            )

            # If we have already seen the RC of this edge, or if we have
            # already seen a parallel edge to this one, then copy that other
            # edge's random index to this one (so that they are assigned the
            # same random color). (We check the RC case first since parallel
            # edges are relatively rare -- I expect the average graph to have
            # many more RC edges than parallel edges.)
            if rcnamepair in edgenamepair2rand_idx:
                new_edge.rand_idx = edgenamepair2rand_idx[rcnamepair]
            elif namepair in edgenamepair2rand_idx:
                new_edge.rand_idx = edgenamepair2rand_idx[namepair]
            else:
                ri = next(rand_idx_generator)

                # To avoid confusion, guarantee that edges do not share the
                # random color of their source or target node. This is
                # especially important for loop edges, which -- depending on
                # Cytoscape.js styling -- can pass through the node body.
                while ri == src.rand_idx or ri == tgt.rand_idx:
                    ri = next(rand_idx_generator)

                new_edge.rand_idx = ri
                edgenamepair2rand_idx[namepair] = ri

        if not lengths_completely_defined:
            raise WeirdError(f"Not all {self.seq_noun}s have defined lengths?")

        # Now that we've seen all of these attributes, turn them from sets to
        # lists so that they have a consistent ordering. This is useful for
        # showing tables of nodes/edges in the visualization.
        # (Also, ignore attributes where the entries were all None.)
        self.extra_node_attrs = sorted(extra_node_attrs_with_atleastone_entry)
        self.extra_edge_attrs = sorted(extra_edge_attrs_with_atleastone_entry)

        # ... And, just to be extra fancy: if this is a LJA / Flye graph where
        # the edges have their own defined IDs, move these to the start of the
        # list so they're shown as the leftmost extra attr in the table
        if "id" in self.extra_edge_attrs:
            self.extra_edge_attrs.remove("id")
            self.extra_edge_attrs = ["id"] + self.extra_edge_attrs

    def _get_unique_id(self):
        """Returns an int guaranteed to be usable as a unique new ID.

        We assign these unique IDs to nodes, edges, patterns, and components.
        We could probably get away with letting there be some overlap between
        node and edge IDs, or between component IDs and other IDs, but it's
        easiest to just give all of these objects unique IDs.
        """
        # this is what they pay me the big bucks for, folks. this is home-grown
        # organic computer science right here
        new_id = self.num_objs
        self.num_objs += 1
        return new_id

    def _make_new_split_node(self, counterpart_node_id, split):
        """Creates a new "split" node based on another node.

        Parameters
        ----------
        counterpart_node_id: int
            ID of the original node from which we'll create this split node.
            This should correspond to an entry in self.nodeid2obj. When we
            create the new Node, its constructor will take care to convert this
            node to the opposite split type as "split" (so, if split is LEFT,
            then the counterpart will become a RIGHT split node, and vice
            versa). (Of course, if the counterpart node is already split for
            some perverse reason, the Node constructor will throw an error.)

        split: str
            Should be either config.SPLIT_LEFT or config.SPLIT_RIGHT.

        Returns
        -------
        new_node_id: int
            The ID of the split node we created.
        """
        counterpart_node = self.nodeid2obj[counterpart_node_id]
        new_node_id = self._get_unique_id()
        # NOTE: Deep copying the data here is probably unnecessary, since I
        # don't think we'll ever *want* it to be different between a node and
        # its split copy. Ideally we'd restructure things so that we could
        # just pass the new node ID, the split, and just the counterpart Node
        # to the Node constructor, and the constructor would extract the name
        # and data accordingly. But whatever, this approach is simple.
        new_node = Node(
            new_node_id,
            counterpart_node.name,
            deepcopy(counterpart_node.data),
            split=split,
            counterpart_node=counterpart_node,
        )
        new_node.rand_idx = counterpart_node.rand_idx
        self.nodeid2obj[new_node_id] = new_node
        return new_node_id

    def _should_split(self, boundary_node_id, exterior_nodes):
        return (
            len(exterior_nodes) > 0
            and boundary_node_id in self.nodeid2obj
            and self.nodeid2obj[boundary_node_id].is_not_split()
        )

    def _add_pattern(self, validation_results):
        """Adds a pattern to the decomposed graph.

        Parameters
        ----------
        validation_results: validators.ValidationResults
            Results from validating this pattern in the assembly graph. We
            assume that this is the result of a *successful* validation, i.e.
            the is_valid attribute of this is True.

        Returns
        -------
        (Pattern, list, list): (pattern, left split IDs, right split IDs)
            pattern: object describing the newly created pattern.

            left split IDs: list of IDs of new left split nodes created
            (located just outside this pattern, each with an outgoing edge to
            their corresponding start Node).

            right split IDs: list of IDs of new right split nodes created
            (located just outside this pattern, each with an incoming edge from
            their corresponding end Node).
        """
        pattern_id = self._get_unique_id()
        self.decomposed_graph.add_node(pattern_id)
        patt_node_ids = set(validation_results.node_ids)

        # We will need to create new Node(s) if we split the start and/or end
        # Node(s) of the pattern. If we create any new Nodes, we'll store their
        # IDs in these variables.
        #
        # NOTE that these new Nodes, if created, will be located OUTSIDE of
        # this pattern (see the diagrams below). The Node IDs in
        # validation_results.node_ids (aka patt_node_ids) will thus remain a
        # "complete" description of all Nodes in this pattern, even if we do
        # splitting.
        left_split_ids = []
        right_split_ids = []

        # Do we need to split the start nodes of this pattern?
        for start_id in validation_results.start_node_ids:
            start_incoming_nodes_outside_pattern = (
                set(self.decomposed_graph.pred[start_id]) - patt_node_ids
            )

            if self._should_split(
                start_id, start_incoming_nodes_outside_pattern
            ):
                # Since this start node has incoming edge(s) from outside the
                # pattern, and since it already isn't a split node, we need to
                # split it.
                # We'll create a new Node for the left split (in the diagram
                # below, "1-L"), and change the existing Node into the right
                # split (in the diagram below, "1-R").

                #    BEFORE     |          AFTER
                #         2     |                     2
                #        / \    |                    / \
                # 0 --> 1   4   |   0 --> 1-L ==> 1-R   4
                #        \ /    |                    \ /
                #         3     |                     3
                left_node_id = self._make_new_split_node(
                    start_id, config.SPLIT_LEFT
                )
                for g in (self.graph, self.decomposed_graph):
                    g.add_node(left_node_id)

                # Route edges from start_incoming_nodes_outside_pattern to
                # the left node.
                #
                # We go through self.graph and self.decomposed_graph separately
                # -- this way we don't have to worry about edge keys matching
                # up between the graphs.
                for incoming_node_id, _, key, data in list(
                    self.decomposed_graph.in_edges(
                        start_id, keys=True, data=True
                    )
                ):
                    if (
                        incoming_node_id
                        in start_incoming_nodes_outside_pattern
                    ):
                        uid = data["uid"]
                        # When we collapse this pattern into a single node in
                        # the decomposed graph, the new split node will still
                        # be located outside of the pattern. Therefore, the
                        # incoming edges of the start node should be rerouted
                        # (in both the uncollapsed and collapsed graph) to
                        # point to the new split node, *not* the collapsed
                        # pattern.
                        self.edgeid2obj[uid].reroute_tgt(left_node_id)
                        self.edgeid2obj[uid].reroute_dec_tgt(left_node_id)
                        # We keep the edge ID the same, so ... even though we
                        # reroute it in the graphs, this is still the same edge.
                        self.decomposed_graph.add_edge(
                            incoming_node_id, left_node_id, uid=uid
                        )
                        self.decomposed_graph.remove_edge(
                            incoming_node_id, start_id, key
                        )

                for incoming_node_id, _, key, data in list(
                    self.graph.in_edges(start_id, keys=True, data=True)
                ):
                    if (
                        incoming_node_id
                        in start_incoming_nodes_outside_pattern
                    ):
                        uid = data["uid"]
                        self.graph.add_edge(
                            incoming_node_id, left_node_id, uid=uid
                        )
                        self.graph.remove_edge(incoming_node_id, start_id, key)

                # All other edges (mostly outgoing edges, but maybe incoming
                # edges from within the pattern) will be routed by default to
                # the right node. Because... the right node is just the
                # original node, but renamed! Cool.

                # Add a fake edge between the left and right node
                fake_edge_id = self._get_unique_id()
                fake_edge = Edge(
                    fake_edge_id, left_node_id, start_id, {}, is_fake=True
                )
                # if we color nodes/edges random colors, then the color of the
                # fake edge should match that of the nodes it is sandwiched
                # between
                fake_edge.rand_idx = self.nodeid2obj[left_node_id].rand_idx
                # If we collapse the pattern we just identified, then the edge
                # points from the new left node (outside of the pattern) to the
                # pattern itself. (If the left node gets added to another
                # pattern later, then we will call reroute_dec_src() on this
                # edge.)
                fake_edge.reroute_dec_tgt(pattern_id)
                self.edgeid2obj[fake_edge_id] = fake_edge
                self.graph.add_edge(left_node_id, start_id, uid=fake_edge_id)
                self.decomposed_graph.add_edge(
                    left_node_id, pattern_id, uid=fake_edge_id
                )
                left_split_ids.append(left_node_id)

        # Do we need to split the end nodes of this pattern?
        for end_id in validation_results.end_node_ids:
            end_outgoing_nodes_outside_pattern = (
                set(self.decomposed_graph.adj[end_id]) - patt_node_ids
            )

            if self._should_split(end_id, end_outgoing_nodes_outside_pattern):
                # Since this end node has outgoing edge(s) to outside the
                # pattern, we need to split it.
                # We'll create a new Node for the right split (in the diagram
                # below, "4-R"), and change the existing Node into the left
                # split (in the diagram below, "4-L").

                #     BEFORE    |          AFTER
                #   2           |     2
                #  / \          |    / \
                # 1   4 --> 5   |   1   4-L ==> 4-R --> 5
                #  \ /          |    \ /
                #   3           |     3
                right_node_id = self._make_new_split_node(
                    end_id, config.SPLIT_RIGHT
                )
                for g in (self.graph, self.decomposed_graph):
                    g.add_node(right_node_id)
                # Route edges from the right node to
                # end_outgoing_nodes_outside_pattern
                for _, outgoing_node_id, key, data in list(
                    self.decomposed_graph.out_edges(
                        end_id, keys=True, data=True
                    )
                ):
                    if outgoing_node_id in end_outgoing_nodes_outside_pattern:
                        uid = data["uid"]
                        self.edgeid2obj[uid].reroute_src(right_node_id)
                        self.edgeid2obj[uid].reroute_dec_src(right_node_id)
                        self.decomposed_graph.add_edge(
                            right_node_id, outgoing_node_id, uid=uid
                        )
                        self.decomposed_graph.remove_edge(
                            end_id, outgoing_node_id, key
                        )

                for _, outgoing_node_id, key, data in list(
                    self.graph.out_edges(end_id, keys=True, data=True)
                ):
                    if outgoing_node_id in end_outgoing_nodes_outside_pattern:
                        uid = data["uid"]
                        self.graph.add_edge(
                            right_node_id, outgoing_node_id, uid=uid
                        )
                        self.graph.remove_edge(end_id, outgoing_node_id, key)

                # Add a fake edge between the left and right node
                fake_edge_id = self._get_unique_id()
                fake_edge = Edge(
                    fake_edge_id, end_id, right_node_id, {}, is_fake=True
                )
                fake_edge.rand_idx = self.nodeid2obj[right_node_id].rand_idx
                fake_edge.reroute_dec_src(pattern_id)
                self.edgeid2obj[fake_edge_id] = fake_edge
                self.graph.add_edge(end_id, right_node_id, uid=fake_edge_id)
                self.decomposed_graph.add_edge(
                    pattern_id, right_node_id, uid=fake_edge_id
                )
                right_split_ids.append(right_node_id)

        # For every edge from outside this pattern to a node within this
        # pattern: route this edge to just point (in the decomposed graph)
        # to the new pattern node.
        #
        # If all of the pattern's boundary nodes were newly split in this
        # function, then I do not think this will change the graph. But often
        # there are lingering edges incident to the pattern node in the
        # decomposed graph (maybe because of not splitting a boundary node,
        # maybe because of weird edges between other stuff in the graph and
        # the middle nodes of a pattern -- not that that should happen with
        # the current kinds of pattern identified by MgSc). So, we have to do
        # this.
        in_edges = self.decomposed_graph.in_edges(patt_node_ids, keys=True)
        p_in_edges = list(
            filter(lambda e: e[0] not in patt_node_ids, in_edges)
        )
        for e in p_in_edges:
            e_uid = self.decomposed_graph.edges[e]["uid"]
            self.edgeid2obj[e_uid].reroute_dec_tgt(pattern_id)
            # We will remove the edge that this is replacing (e) soon, when we
            # call self.decomposed_graph.remove_nodes_from(patt_node_ids).
            self.decomposed_graph.add_edge(e[0], pattern_id, uid=e_uid)

        # For every edge from inside this pattern to a node outside this
        # pattern: route this edge to originate from (in the decomposed
        # graph) the new pattern node. Like above.
        out_edges = self.decomposed_graph.out_edges(patt_node_ids, keys=True)
        p_out_edges = list(
            filter(lambda e: e[1] not in patt_node_ids, out_edges)
        )
        for e in p_out_edges:
            e_uid = self.decomposed_graph.edges[e]["uid"]
            self.edgeid2obj[e_uid].reroute_dec_src(pattern_id)
            # again, don't worry, we'll remove the edge this is replacing soon
            self.decomposed_graph.add_edge(pattern_id, e[1], uid=e_uid)

        # Extract the actual Node and Edge objects in this Pattern, so we can
        # pass references to these objects to the Pattern
        child_nodes = []
        for uid in patt_node_ids:
            if uid in self.nodeid2obj:
                child_nodes.append(self.nodeid2obj[uid])
            else:
                # Implicitly, this will cause an error if uid is not a Node
                # *or* Pattern ID.
                child_nodes.append(self.pattid2obj[uid])
        subgraph = self.decomposed_graph.subgraph(patt_node_ids).copy()
        child_edges = [
            self.edgeid2obj[uid] for _, _, uid in subgraph.edges(data="uid")
        ]

        p = Pattern(
            pattern_id,
            validation_results,
            child_nodes,
            child_edges,
        )

        # If this Pattern was a chain or cyclic chain, and any of its child
        # nodes were collapsed chains, then these child chains will be merged
        # into this Pattern when we call Pattern(). Although the Pattern
        # constructor updates the nodes and edges that this new Pattern has
        # accordingly, we still need to re-route edges and update the
        # decomposed assembly graph's topology here.
        #
        # NOTE: there is the chance that we might need to merge multiple
        # child chains in at once. In this case, there may be edges between
        # these child chains -- so, we include the IDs of these child chains in
        # patt_node_ids_post_merging. (if we don't do this, it screws with the
        # edge dec src/tgt IDs, which then screws with unnecessary split node
        # removal.) See test_chr21mat_minus653300458_splits_merged() in the
        # hierarchical decomposition tests.
        patt_node_ids_post_merging = p.get_node_ids() + [
            t.unique_id for t in p.merged_child_chains
        ]
        for mcc in p.merged_child_chains:
            if mcc.pattern_type != config.PT_CHAIN:
                raise WeirdError(f"Can't merge {mcc} into {p}?")
            pred = self.decomposed_graph.pred[mcc.unique_id]
            # TODO: check for cascading effects, or lack thereof? and see WHERE
            # the src/tgt rerouting of edge 336 is being done. if here, then
            # i'd bet it should be reverting instead. how can we make that
            # change? oh, maybe it's because none of the src/tgt of this edge
            # is in patt_node_ids_post_merging; check if src/tgt are in
            # p.merged_Child_chains, maybe, and handle specially? or something
            # ^^^ 2025 update: i forget what the above text means. try it out
            # with the "full" chr15 version maybe
            for incoming_node in pred:
                if incoming_node in patt_node_ids_post_merging:
                    for e in pred[incoming_node]:
                        self.edgeid2obj[
                            pred[incoming_node][e]["uid"]
                        ].revert_dec_tgt()
                else:
                    for e in pred[incoming_node]:
                        self.edgeid2obj[
                            pred[incoming_node][e]["uid"]
                        ].reroute_dec_tgt(pattern_id)

            adj = self.decomposed_graph.adj[mcc.unique_id]
            for outgoing_node in adj:
                if outgoing_node in patt_node_ids_post_merging:
                    for e in adj[outgoing_node]:
                        self.edgeid2obj[
                            adj[outgoing_node][e]["uid"]
                        ].revert_dec_src()
                else:
                    for e in adj[outgoing_node]:
                        self.edgeid2obj[
                            adj[outgoing_node][e]["uid"]
                        ].reroute_dec_src(pattern_id)
            self.chains.remove(mcc)
            del self.pattid2obj[mcc.unique_id]

        # Remove the children of this pattern (and any edges incident on them,
        # which should be limited -- after the splitting and rerouting steps
        # above -- to edges in child_edges) from the decomposed DiGraph.
        #
        # NOTE that we use patt_node_ids instead of patt_node_ids_post_merging
        # because, although the contents of the merged chain(s) (if any) have
        # already been removed from the decomposed graph, these merged chain(s)
        # themselves have not.
        self.decomposed_graph.remove_nodes_from(patt_node_ids)

        self.pattid2obj[pattern_id] = p
        self.ptype2collection[validation_results.pattern_type].append(p)
        return p, left_split_ids, right_split_ids

    def _hierarchically_identify_patterns(self):
        """Run all of our pattern detection algorithms on the graph repeatedly.

        TODOs: code
        -----------
        6. See if we can move the splitting code in _add_pattern() to another
           helper function (that takes as input the graph and decomposed
           graph?), or something? if feasible.
        """
        while True:
            something_collapsed_in_this_iteration = False
            # The use of set here means that the order in which we go through
            # nodes is technically arbitrary. However, I don't think this makes
            # a big difference, if any...?
            candidate_nodes = set(self.decomposed_graph.nodes)
            while len(candidate_nodes) > 0:
                # NOTE that, in uncommon cases, we could -- while using n as
                # the starting node -- identify a pattern that does not include
                # n (for example, if n is the start of a bubble that contains
                # another bubble within it). In this case, we will still pop n
                # from the set of candidate nodes here; n will remain in the
                # decomposed graph, so we'll still revisit it in the next
                # iteration of the outer while loop. (We could avoid popping
                # and keep n in candidate_nodes just so we can revisit it
                # within this iteration of the outer while loop, but that makes
                # this code uglier for maaaaybe a rare slight performance
                # benefit.)
                n = candidate_nodes.pop()

                # You could switch the order of this tuple up in order to
                # change the "precedence" of pattern detection, if desired.
                # I don't thiiiiink this should make a difference, due to (1)
                # automatic boundary duplication and (2) the guarantee of
                # minimality (each bulge, chain, bubble, and cyclic chain
                # are guaranteed not to contain any undetected smaller patterns
                # within them).
                #
                # However, maybe the order could matter in a way that I'm not
                # thinking of right now -- I mean, I haven't written out a
                # formal proof or anything. Leave a comment at
                # https://github.com/marbl/MetagenomeScope/issues/13 if you
                # have opinions. If you don't have opinions but you're reading
                # this anyway, please react to issue 13 with the :eyes: emoji
                # because I think that would be funny.
                for pass_objs, validator in (
                    (False, validators.is_valid_bulge),
                    (True, validators.is_valid_chain_trimmed_etfes),
                    (True, validators.is_valid_bubble),
                    (False, validators.is_valid_cyclic_chain),
                ):
                    # Does this type of pattern start at this node?
                    # (pass_objs just controls whether or not we need to pass
                    # the nodeid2obj and edgeid2obj variables to the validator;
                    # mainly need as of writing due to the ETFE-trimming stuff
                    # with chains)
                    if pass_objs:
                        validation_results = validator(
                            self.decomposed_graph,
                            n,
                            self.nodeid2obj,
                            self.edgeid2obj,
                        )
                    else:
                        validation_results = validator(
                            self.decomposed_graph, n
                        )

                    if validation_results:
                        # Yes, it does!
                        pobj, left_splits, right_splits = self._add_pattern(
                            validation_results
                        )

                        # Remove child nodes of this pattern from consideration as
                        # future start nodes of other patterns. (Don't worry,
                        # self._add_pattern() already takes care of removing them
                        # from the decomposed graph.)
                        for pn in pobj.nodes:
                            # We use .discard() rather than .remove() since we
                            # already popped n from candidate_nodes (and .remove()
                            # throws an error if we try to remove an element that
                            # isn't present in the set)
                            candidate_nodes.discard(pn.unique_id)

                        # If the creation of pobj involved merging child
                        # chain(s) into it, we should remove these child chains
                        # from consideration as candidate nodes.
                        for pn in pobj.merged_child_chains:
                            candidate_nodes.discard(pn.unique_id)

                        # We don't need to add the new pattern object itself (or the
                        # left split nodes) to candidate_nodes, but we add
                        #
                        # (1) the right split nodes, and
                        # (2) the incoming nodes [located outside of the newly-
                        #     identified pattern] of the left split nodes
                        #
                        # The reason for only adding these nodes: we know that
                        # the left split nodes and the new pattern node can't
                        # be the start of a chain, cyclic chain, bulge, bubble,
                        # frayed rope, or bipartite. (The use of
                        # is_valid_chain_trimmed_etfes() prevents us from
                        # identifying these as the start of "chains.") They
                        # could be located *within* a pattern that starts at
                        # another node, though, which is why we add the
                        # incoming nodes of the left splits.
                        for rs in right_splits:
                            candidate_nodes.add(rs)
                        for ls in left_splits:
                            for incoming_node in self.decomposed_graph.pred[
                                ls
                            ]:
                                # thinking about this later, I'm not sure any
                                # of the patterns we identify will have
                                # outgoing edges to a left split node at this
                                # point. may as well be safe tho
                                if incoming_node not in pobj.get_node_ids():
                                    candidate_nodes.add(incoming_node)

                        something_collapsed_in_this_iteration = True

                        # Don't bother trying to identify the start of any other
                        # patterns at n, since n is no longer present in the
                        # decomposed graph.
                        break

            if not something_collapsed_in_this_iteration:
                # We just went through every top-level node in the decomposed
                # graph and didn't collapse anything -- we can exit the outer
                # while loop.
                break

        # Now, identify frayed ropes and bipartites ("top-level only" patterns)
        top_level_candidate_nodes = set(self.decomposed_graph.nodes)
        while len(top_level_candidate_nodes) > 0:
            n = top_level_candidate_nodes.pop()
            for validator in (
                validators.is_valid_frayed_rope_tl_only,
                validators.is_valid_bipartite_tl_only,
            ):
                validation_results = validator(
                    self.decomposed_graph, n, self.pattid2obj
                )
                if validation_results:
                    # Mostly the same logic as for when we found a pattern above.
                    pobj, left_splits, right_splits = self._add_pattern(
                        validation_results
                    )
                    for pn in pobj.nodes:
                        top_level_candidate_nodes.discard(pn.unique_id)
                    for rs in right_splits:
                        top_level_candidate_nodes.add(rs)
                    for ls in left_splits:
                        for incoming_node in self.decomposed_graph.pred[ls]:
                            if incoming_node not in pobj.get_node_ids():
                                top_level_candidate_nodes.add(incoming_node)
                    if len(pobj.merged_child_chains) > 0:
                        raise WeirdError(
                            f"Shouldn't have done chain merging on {pobj}?"
                        )
                    break

        self._remove_unnecessary_split_nodes()

        # No need to go through the nodes and edges in the top level of the
        # graph and record that they don't have a parent pattern -- their
        # parent_id attrs default to None

    def _remove_unnecessary_split_nodes(self):
        """Removes "unnecessary" split nodes from the graph.

        The purpose of creating split nodes is to allow the same node to
        serve as the start and end of two separate patterns, but this will
        not be the fate of all split nodes. After we have finished pattern
        identification, we say that a split node S (with a counterpart node of
        C) is "unnecessary" if, in the hierarchical decomposition, S is a
        sibling of any ancestor pattern of C.

        In practice, we can just look at the fake edge between S and C in the
        decomposed graph to figure out what this potential sibling ancestor of
        C is.

        Here, we identify and remove unnecessary split nodes in order to
        simplify the visualization.
        """
        for node in list(self.nodeid2obj.values()):
            node_id = node.unique_id
            if node.counterpart_node_id is not None:
                counterpart = self.nodeid2obj[node.counterpart_node_id]
                if counterpart.parent_id is None:
                    # If "counterpart" is not located within a pattern, then we
                    # should be trying to deem "counterpart" as unnecessary
                    # (rather than trying to deem "node" as unnecessary). We'll
                    # get to it later.
                    if node.parent_id is None:
                        # This should never happen: at least one of (node,
                        # counterpart) must be located within a pattern. Due to
                        # chain merging stuff, they might actually be siblings
                        # within a pattern (see below), but if splitting has
                        # been done then at least one of them must be a child
                        # of SOME pattern. (If this case happens, bail out with
                        # an error so we can debug it.)
                        raise WeirdError(
                            f"Split node {node} and counterpart {counterpart} "
                            "both have no parent pattern?"
                        )
                    # Okay, since the above horrible WeirdError didn't trigger,
                    # we know that "node" is actually the child of a pattern.
                    # We'll leave "node" around and remove "counterpart" later.
                    continue

                # If we've made it here, then we have to do some extra work to
                # figure out if we should remove "node". (If the answer is
                # "yes, we should remove it," then we'll set do_removal=True.)
                do_removal = False

                # Figure out where the other end of this node's fake edge
                # points in the decomposed graph.
                if node.split == config.SPLIT_LEFT:
                    fe_id = graph_utils.get_only_connecting_edge_uid(
                        self.graph, node_id, counterpart.unique_id
                    )
                    counterpart_fe_id = self.edgeid2obj[fe_id].dec_tgt_id
                else:
                    fe_id = graph_utils.get_only_connecting_edge_uid(
                        self.graph, counterpart.unique_id, node_id
                    )
                    counterpart_fe_id = self.edgeid2obj[fe_id].dec_src_id

                # In strange cases (due to chain merging, I think), a split
                # node and its counterpart can be children of the same parent
                # pattern. In this case, they should obviously be merged back
                # together (it doesn't really matter if we remove "node" or
                # "counterpart" in this case).
                if node.parent_id == counterpart.parent_id:
                    do_removal = True
                else:
                    # Okay, we're still not sure if we need to remove "node".
                    #
                    # If we see here that the fake edge points to the
                    # counterpart node directly, we know that "node" is located
                    # "further down" the hierarchy than "counterpart".
                    #
                    # Like the "if counterpart.parent_id is None" check above,
                    # we should be trying to deem *that* node as unnecessary,
                    # and we'll get to it later.
                    if counterpart_fe_id not in self.pattid2obj:
                        if counterpart_fe_id not in self.nodeid2obj:
                            # Probably what happened here is -- the counterpart
                            # ID corresponds to a pattern that has since been
                            # removed from the graph. The chain merging process
                            # is surprisingly complex, and has triggered this
                            # kind of bug in the past.
                            raise WeirdError(
                                f"Fake edge {fe_id} between split node {node} "
                                f"and counterpart {counterpart} points to "
                                f"node ID {counterpart_fe_id} in the "
                                "decomposed graph; this ID doesn't seem like "
                                "a pattern OR a non-pattern node?"
                            )
                        # If we've made it here, then "counterpart" corresponds
                        # to a top-level non-pattern node in the fully
                        # decomposed graph.
                        continue

                    # If we've made it here, this fake edge points to an
                    # ancestor of this node's counterpart. Figure out what the
                    # parent (if any) of *that* ancestor is.
                    counterpart_ancestor_parent_id = self.pattid2obj[
                        counterpart_fe_id
                    ].parent_id

                    # If this node is a sibling of the counterpart ancestor, then
                    # this node is unnecessary. Note that this conditional is True
                    # even if both parent_ids are None.
                    if node.parent_id == counterpart_ancestor_parent_id:
                        # ok yep it's unnecessary, remove it
                        do_removal = True

                if do_removal:
                    if node.split == config.SPLIT_LEFT:
                        # remove the fake edge from L ==> R
                        self.graph.remove_edge(
                            node_id, counterpart.unique_id, 0
                        )
                        if node.parent_id is None:
                            self.decomposed_graph.remove_edge(
                                node_id, counterpart_fe_id, 0
                            )

                        # In the uncollapsed graph, route incoming edges to now
                        # have a target of the original node (in the graph).
                        for in_edge in list(
                            self.graph.in_edges(node_id, keys=True, data=True)
                        ):
                            e_uid = in_edge[3]["uid"]
                            edge = self.edgeid2obj[e_uid]
                            edge.reroute_tgt(counterpart.unique_id)
                            edge.reroute_dec_tgt(counterpart_fe_id)
                            self.graph.add_edge(
                                in_edge[0],
                                counterpart.unique_id,
                                uid=e_uid,
                            )
                            self.graph.remove_edge(
                                in_edge[0], node_id, in_edge[2]
                            )
                        # In the decomposed graph, route incoming edges to now
                        # have a target of the original node's parent pattern.
                        # (Calling edge.reroute_dec_tgt() above took care of
                        # updating the actual Edge objects, but we still need
                        # to update the topology of the decomposed graph if
                        # "node" is present in its top level.)
                        if node.parent_id is None:
                            for in_edge in list(
                                self.decomposed_graph.in_edges(
                                    node_id, keys=True, data=True
                                )
                            ):
                                e_uid = in_edge[3]["uid"]
                                edge = self.edgeid2obj[e_uid]
                                self.decomposed_graph.add_edge(
                                    edge.dec_src_id,
                                    counterpart_fe_id,
                                    uid=e_uid,
                                )
                                self.decomposed_graph.remove_edge(
                                    edge.dec_src_id, node_id, in_edge[2]
                                )

                    elif node.split == config.SPLIT_RIGHT:
                        # again, rm the fake edge
                        self.graph.remove_edge(
                            counterpart.unique_id, node_id, 0
                        )
                        if node.parent_id is None:
                            self.decomposed_graph.remove_edge(
                                counterpart_fe_id, node_id, 0
                            )

                        for out_edge in list(
                            self.graph.out_edges(node_id, keys=True, data=True)
                        ):
                            e_uid = out_edge[3]["uid"]
                            edge = self.edgeid2obj[e_uid]
                            edge.reroute_src(counterpart.unique_id)
                            edge.reroute_dec_src(counterpart_fe_id)
                            self.graph.add_edge(
                                counterpart.unique_id,
                                out_edge[1],
                                uid=e_uid,
                            )
                            self.graph.remove_edge(
                                node_id, out_edge[1], out_edge[2]
                            )
                        if node.parent_id is None:
                            for out_edge in list(
                                self.decomposed_graph.out_edges(
                                    node_id, keys=True, data=True
                                )
                            ):
                                e_uid = out_edge[3]["uid"]
                                edge = self.edgeid2obj[e_uid]
                                self.decomposed_graph.add_edge(
                                    counterpart_fe_id,
                                    edge.dec_tgt_id,
                                    uid=e_uid,
                                )
                                self.decomposed_graph.remove_edge(
                                    node_id, edge.dec_tgt_id, out_edge[2]
                                )
                    else:
                        raise WeirdError(
                            f"{node} has a split attribute of {node.split}?"
                        )
                    self.graph.remove_node(node_id)
                    if node.parent_id is not None:
                        # remove this node, and the associated fake edge, from
                        # the children of this parent pattern (pp).
                        pp = self.pattid2obj[node.parent_id]
                        # This removal may require that we re-assign the start
                        # and/or end node of this parent pattern
                        if node_id in pp.start_node_ids:
                            pp.start_node_ids.remove(node_id)
                            pp.start_node_ids.append(counterpart_fe_id)
                        if node_id in pp.end_node_ids:
                            pp.end_node_ids.remove(node_id)
                            pp.end_node_ids.append(counterpart_fe_id)
                        pp.nodes.remove(node)
                        pp.edges.remove(self.edgeid2obj[fe_id])
                    else:
                        self.decomposed_graph.remove_node(node_id)
                    counterpart.unsplit()
                    del self.nodeid2obj[node_id]
                    del self.edgeid2obj[fe_id]

    def get_component_node_and_edge_cts(self):
        """Returns lists of node and edge counts for each component.

        Currently, this returns counts of "full" nodes -- treating each split
        node A-L and A-R as a single node, but also treating
        reverse-complementary nodes separately (so, if a component contains
        both node A and node -A, then this will count as two nodes).

        And it returns counts of "real" edges, ignoring the fake ones created
        by node splitting.

        So like the takeaway here is that this is the kind of helpful
        information we want to actually SHOW to the user lol

        Returns
        -------
        (node_cts, edge_cts): (list of int, list of int)
            Lists of counts of nodes and edges in each component. These lists
            are guaranteed to have the same lengths. Furthermore, they are in
            the same order -- so the same component is described by position X
            in node_cts and by position X in edge_cts.
        """
        cc_node_cts = []
        cc_edge_cts = []
        for cc in self.components:
            cc_node_cts.append(cc.num_full_nodes)
            cc_edge_cts.append(cc.num_real_edges)
        return cc_node_cts, cc_edge_cts

    def get_node_lengths(self):
        """Returns a dict mapping node IDs to lengths.

        If a node does not have a corresponding length available, then this
        node will not be represented in the returned dict. If no nodes have
        lengths, this will return {}.

        This will raise a WeirdError if we see any split nodes in the graph.
        You should call this before doing the pattern decomposition stuff!
        """
        lengths = {}
        for ni, n in self.nodeid2obj.items():
            if n.split is not None:
                raise WeirdError(
                    f"Split nodes shouldn't exist in the graph yet: {n}"
                )
            if "length" in n.data:
                lengths[ni] = n.data["length"]
        return lengths

    def _scale_nodes_all_uniform(self):
        for node in self.nodeid2obj.values():
            if "orientation" in node.data:
                node.relative_length = 0.5
                node.longside_proportion = config.MID_LONGSIDE_PROPORTION

    def _scale_nodes(self):
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
        However, MetagenomeScope can now show multiple components at once, so
        we scale nodes based on the min/max lengths throughout the entire
        graph.

        Notes
        -----
        If either of the following conditions are met:

        1. at least one of the graph's nodes does not have a "length" attribute
        2. all nodes in the graph have the same "length" attribute

        ...Then this will assign each node a relative_length of 0.5 and a
        longside_proportion of config.MID_LONGSIDE_PROPORTION.

        (TODO, just omit these or something instead? would slim down the
        visualization filesize.)
        """
        # dict that maps node IDs --> lengths
        node_lengths = self.get_node_lengths()

        # bail out if not all nodes have a length
        if len(node_lengths) < len(self.graph.nodes):
            self._scale_nodes_all_uniform()
        else:
            node_length_values = node_lengths.values()
            min_len = min(node_length_values)
            max_len = max(node_length_values)

            # bail out if all nodes have equal lengths
            if min_len == max_len:
                self._scale_nodes_all_uniform()
            else:
                # okay, if we've made it here we can actually do node scaling
                node_log_lengths = {}
                for node_id, length in node_lengths.items():
                    node_log_lengths[node_id] = math.log(
                        length, config.NODE_SCALING_LOG_BASE
                    )
                min_log_len = min(node_log_lengths.values())
                max_log_len = max(node_log_lengths.values())
                log_len_range = max_log_len - min_log_len
                q25, q75 = numpy.percentile(
                    list(node_log_lengths.values()), [25, 75]
                )
                for node_id in self.nodeid2obj:
                    node_log_len = node_log_lengths[node_id]
                    self.nodeid2obj[node_id].relative_length = (
                        node_log_len - min_log_len
                    ) / log_len_range
                    if node_log_len < q25:
                        lp = config.LOW_LONGSIDE_PROPORTION
                    elif node_log_len < q75:
                        lp = config.MID_LONGSIDE_PROPORTION
                    else:
                        lp = config.HIGH_LONGSIDE_PROPORTION
                    self.nodeid2obj[node_id].longside_proportion = lp

    def _compute_node_dimensions(self):
        r"""Adds height and width attributes to each node in the graph.

        It is assumed that _scale_nodes() has already been called; otherwise,
        this will be unable to access the relative_length and
        longside_proportion node attributes, which will cause a KeyError.

        This only covers "bottom-level" nodes -- i.e. patterns are not assigned
        dimensions, since those should be scaled based on the bounding box
        needed to contain their child elements. However, "duplicate" nodes
        should be assigned dimensions, since for all intents and purposes
        they're "real". (It may be possible to speed this up slightly by only
        duplicating data for these nodes after doing scaling, etc., but I doubt
        that the time savings there will be that useful in most cases.)

        In previous versions of MetagenomeScope (that laid out the graph using
        the default top --> bottom "rankdir"), the width and height of nodes
        were flipped. Now that we lay out the graph from left to right, the
        width and height are no longer flipped, so this code should be way less
        confusing.
        """
        for node in self.nodeid2obj.values():
            if node.relative_length is not None:
                area = config.MIN_NODE_AREA + (
                    node.relative_length * config.NODE_AREA_RANGE
                )
                node.width = area**node.longside_proportion
                node.height = area / node.width
            else:
                # TODO make into a config variable
                # matches flye's graphs' node sizes
                node.width = node.height = 0.3

    def get_edge_weight_field(
        self, field_names=["bsize", "multiplicity", "cov", "kmer_cov"]
    ):
        """Returns the name of the edge weight field this graph has.

        If the graph does not have any edge weight fields, or if only some
        edges have an edge weight field, returns None.

        If there are multiple edge weight fields, this raises a
        GraphParsingError. If any of the edges in the graph are fake, this
        raises a WeirdError.

        The list of field names corresponding to "edge weights" is
        configurable via the field_names parameter. You should verify (in the
        assembly graph parsers) that these fields correspond to positive
        numbers.

        Notes
        -----
        - This entire function should be removed, eventually, in favor of
          letting the user dynamically choose how to adjust edge weights in the
          browser.

        - It should be possible to merge this function with _init_graph_objs();
          this would speed things up, since we could avoid iterating through
          the edges in the graph here. But not worth it right now.
        """

        def _check_edge_weight_fields(edge_data):
            edge_fns = set(edge_data.keys()) & set(field_names)
            if len(edge_fns) > 1:
                raise GraphParsingError(
                    f"Graph has multiple 'edge weight' fields ({edge_fns}). "
                    "It's ambiguous which we should use for scaling."
                )
            elif len(edge_fns) == 1:
                return list(edge_fns)[0]
            else:
                return None

        chosen_fn = None
        for e in self.edgeid2obj.values():
            if e.is_fake:
                raise WeirdError(
                    "Fake edges shouldn't exist in the graph yet."
                )
            fn = _check_edge_weight_fields(e.data)
            if fn is None:
                return None
            else:
                if chosen_fn is None:
                    chosen_fn = fn
                else:
                    if chosen_fn != fn:
                        raise GraphParsingError(
                            "One edge has only the 'edge weight' field "
                            f"{chosen_fn}, while another has only {fn}. "
                            "It's ambiguous how we should do scaling."
                        )
        return chosen_fn

    def _scale_edges(self):
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
            """Assigns "normal" attributes to each Edge object in edges."""
            for edge in edges:
                edge.is_outlier = 0
                edge.relative_weight = 0.5

        # self.get_edge_weight_field() will throw an error if any of the
        # current edges in the graph are fake (we should not have done
        # hierarchical decomposition yet!) -- this way, we can assume for the
        # rest of this function that all edges in the graph are real
        ew_field = self.get_edge_weight_field()
        if ew_field is not None:
            operation_msg("Scaling edges based on weights...")
            weights = []
            for edge in self.edgeid2obj.values():
                weights.append(edge.data[ew_field])

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
                for edge in self.edgeid2obj.values():
                    ew = edge.data[ew_field]
                    if ew > uf:
                        edge.is_outlier = 1
                        edge.relative_weight = 1
                    elif ew < lf:
                        edge.is_outlier = -1
                        edge.relative_weight = 0
                    else:
                        edge.is_outlier = 0
                        non_outlier_edges.append(edge)
                        non_outlier_edge_weights.append(ew)
            else:
                # There are < 4 edges, so consider all edges as "non-outliers."
                for edge in self.edgeid2obj.values():
                    edge.is_outlier = 0
                    non_outlier_edges.append(edge)
                    ew = edge.data[ew_field]
                    non_outlier_edge_weights.append(ew)

            # Perform relative scaling for non-outlier edges, if possible.
            if len(non_outlier_edges) >= 2:
                min_ew = min(non_outlier_edge_weights)
                max_ew = max(non_outlier_edge_weights)
                if min_ew != max_ew:
                    ew_range = max_ew - min_ew
                    for edge in non_outlier_edges:
                        ew = edge.data[ew_field]
                        rw = (ew - min_ew) / ew_range
                        edge.relative_weight = rw
                else:
                    # Can't do edge scaling, so just assign this list of edges
                    # (... which should in practice just be a list with one or
                    # zero edges, I guess...?) "default" edge weight attributes
                    _assign_default_weight_attrs(non_outlier_edges)
            conclude_msg()
        else:
            # Can't do edge scaling, so just assign every edge "default" attrs
            _assign_default_weight_attrs(self.edgeid2obj.values())

    def is_pattern(self, node_id):
        """Returns True if a node ID is for a pattern, False otherwise.

        The node ID should be a nonnegative integer. If it seems invalid,
        this'll throw an error -- mostly to prevent me from messing things
        up and this silently returning False or whatever. Programming is hard!
        """
        if node_id >= self.num_objs or node_id < 0:
            raise WeirdError(f"Node ID {node_id} seems out of range.")
        return node_id in self.pattid2obj

    def _record_connected_components(self):
        """Stores information about weakly connected components in the graph.

        This initializes self.components, a list of Components that is sorted
        in descending order by three criteria: number of nodes, number of
        edges, and number of patterns.
        """
        components = []
        for cc in nx.weakly_connected_components(self.decomposed_graph):
            cobj = Component(self._get_unique_id())
            for node_id in cc:
                if self.is_pattern(node_id):
                    # Component.add_pattern() will take care of adding
                    # information about all descendant nodes/edges/patterns of
                    # this pattern
                    cobj.add_pattern(self.pattid2obj[node_id])
                else:
                    cobj.add_node(self.nodeid2obj[node_id])
                # Record all of the top-level edges in this component by
                # looking at the outgoing edges of each "node", whether it's a
                # real or collapsed-pattern node. (Don't worry, this includes
                # parallel edges.)
                #
                # We could also create the induced subgraph of this component's
                # nodes (in "cc") and then count the number of edges there, but
                # I think this is more efficient.
                for src_id, tgt_id, data in self.decomposed_graph.out_edges(
                    node_id, data=True
                ):
                    cobj.add_edge(self.edgeid2obj[data["uid"]])
            components.append(cobj)

        # The number of "full" nodes (i.e. ignoring node splitting) MUST be the
        # highest-priority sorting criterion. Otherwise, we will be unable to
        # say that an aggregated group of components with the exact same
        # amount of nodes represents a continuous range of component size
        # ranks. See the treemap plot code.
        self.components = sorted(
            components,
            key=lambda cobj: (
                cobj.num_full_nodes,
                cobj.num_total_nodes,
                cobj.num_total_edges,
                cobj.pattern_stats.sum(),
            ),
            reverse=True,
        )
        # Label each component with a "cc_num" indicating how relatively large
        # it is. Useful for searching later on.
        for i, cc in enumerate(self.components, 1):
            cc.set_cc_num(i)

    def __repr__(self):
        return (
            f"AssemblyGraph: {len(self.nodeid2obj):,} Node(s), "
            f"{len(self.edgeid2obj):,} Edge(s), "
            f"{len(self.pattid2obj):,} Pattern(s), "
            f"{len(self.components):,} Component(s)"
        )

    def layout(self):
        """Lays out the assembly graph."""
        logging.info("Laying out the graph...")
        self._layout()
        logging.info("...Finished laying out the graph.")

        logging.info("Rotating and scaling things as needed...")
        self._rotate_from_TB_to_LR()
        logging.info("...Done.")

        self.layout_done = True

    def _layout(self):
        """Lays out the graph's components, handling patterns specially."""
        # Do layout one component at a time.
        first_small_component = False
        for cc_i, cc_tuple in enumerate(self.components):
            cc_node_ids = cc_tuple[0]
            cc_full_node_ct = cc_tuple[1]
            cc_full_edge_ct = cc_tuple[2]

            if cc_full_node_ct >= 5:
                operation_msg(
                    "Laying out component {:,} ({:,} nodes, {:,} edges)...".format(
                        cc_i, cc_full_node_ct, cc_full_edge_ct
                    )
                )
            else:
                if not first_small_component:
                    operation_msg(
                        "Laying out small (each containing < 5 nodes) "
                        "remaining component(s)..."
                    )
                    first_small_component = True

            # If this component contains just one basic node, and no edges or
            # patterns, then we can "fake" its layout. This lets us avoid
            # calling PyGraphviz a gazillion times, and speeds things up (esp
            # for large graphs with gazillions of 1-node components).
            # As a TODO, we can probs generalize this to other types of simple
            # components -- e.g. components with just one loop edge (since we
            # don't even use the control points from loop edges right now), etc
            if cc_full_node_ct == 1 and cc_full_edge_ct == 0:
                # Get the single value from the set without actually popping
                # it, because knowing my luck I feel like that would cause
                # problems.
                # https://stackoverflow.com/questions/59825#comment67384382_60233
                lone_node_id = next(iter(cc_node_ids))
                if not self.is_pattern(lone_node_id):
                    # Alright, we can fake this! Nice.
                    data = self.graph.nodes[lone_node_id]
                    data["cc_num"] = cc_i
                    data["x"] = data["width"] / 2
                    data["y"] = data["height"] / 2
                    self.cc_num_to_bb[cc_i] = (
                        data["width"] + 0.1,
                        data["height"] + 0.1,
                    )
                    continue

            # Lay out this component, using the node and edge data for
            # top-level nodes and edges as well as the width/height computed
            # for "pattern nodes" (in which other nodes, edges, and patterns
            # can be contained).
            gv_input = layout_utils.get_gv_header()

            # Populate GraphViz input with node information
            # This mirrors what's done in Pattern.layout().
            # Also, while we're at it, set component numbers to make traversal
            # easier later on.
            for node_id in cc_node_ids:
                if self.is_pattern(node_id):
                    # TODO i forget what the cc_num stuff is doing here ???
                    # it should already now be set for all nodes,edges,& patts.
                    # Lay out the pattern in isolation (could involve multiple
                    # layers, since patterns can contain other patterns).
                    self.pattid2obj[node_id].layout()
                    height = self.pattid2obj[node_id].height
                    width = self.pattid2obj[node_id].width
                    shape = self.pattid2obj[node_id].shape
                else:
                    data = self.graph.nodes[node_id]
                    data["cc_num"] = cc_i
                    height = data["height"]
                    width = data["width"]
                    shape = data["shape"]
                gv_input += "\t{} [height={},width={},shape={}];\n".format(
                    node_id, height, width, shape
                )

            # Add edge info.
            top_level_edges = self.decomposed_graph.subgraph(cc_node_ids).edges
            for edge in top_level_edges:
                gv_input += "\t{} -> {};\n".format(edge[0], edge[1])
                self.decomposed_graph.edges[edge]["cc_num"] = cc_i

            gv_input += "}"
            top_level_cc_graph = pygraphviz.AGraph(gv_input)
            # Actually perform layout for this component!
            # If you're wondering why MetagenomeScope is taking so long to run
            # on your graph and you traced your way back to this line of code,
            # then boy do I have an NP-Hard problem for you .____________.
            top_level_cc_graph.layout(prog="dot")

            # Output the layout info for this component to an xdot file
            # (TODO, reenable with the -px option; will be nice for debugging)
            # top_level_cc_graph.draw("cc_{}.xdot".format(cc_i))

            self.cc_num_to_bb[cc_i] = layout_utils.get_bb_x2_y2(
                top_level_cc_graph.graph_attr["bb"]
            )

            # Go through _all_ nodes, edges, and patterns within this
            # component and set final position information. Nodes and edges
            # within patterns will need to be updated based on their parent
            # pattern's position information.
            for node_id in cc_node_ids:
                gv_node = top_level_cc_graph.get_node(node_id)
                # The (x, y) position for this node describes its center pos
                x, y = layout_utils.getxy(gv_node.attr["pos"])

                if self.is_pattern(node_id):
                    patt = self.pattid2obj[node_id]
                    patt.set_bb(x, y)

                    # "Reconcile" child nodes, edges, and patterns' relative
                    # positions with the absolute position of this pattern in
                    # the layout.
                    # We go arbitrarily deep here, since patterns can contain
                    # other patterns (which can contain other patterns, ...)
                    #
                    # We use a FIFO queue where each element is a 2-tuple of
                    # (Pattern object, parent Pattern object). This storage
                    # method lets us easily associate patterns with their
                    # parent patterns, and traverse the patterns in such a way
                    # that whenever we get to a given pattern we've already
                    # determined coordinate info for its parent.
                    #
                    # (Of course, patterns at the top level don't have a
                    # parent, hence the None in the second element of the tuple
                    # below.)
                    patt_queue = deque([patt])
                    while len(patt_queue) > 0:
                        # Get the first pattern added
                        curr_patt = patt_queue.popleft()
                        for child_node_id in curr_patt.node_ids:
                            if self.is_pattern(child_node_id):
                                new_patt = self.pattid2obj[child_node_id]
                                # Set pattern bounding box
                                cx = curr_patt.left + new_patt.relative_x
                                cy = curr_patt.bottom + new_patt.relative_y
                                new_patt.set_bb(cx, cy)
                                # Add patterns within this pattern to the end of
                                # the queue
                                patt_queue.append(new_patt)
                            else:
                                # Reconcile data for this normal node within a
                                # pattern
                                data = self.graph.nodes[child_node_id]
                                data["x"] = curr_patt.left + data["relative_x"]
                                data["y"] = (
                                    curr_patt.bottom + data["relative_y"]
                                )

                        for edge in curr_patt.subgraph.edges:
                            data = curr_patt.subgraph.edges[edge]
                            data["ctrl_pt_coords"] = (
                                layout_utils.shift_control_points(
                                    data["relative_ctrl_pt_coords"],
                                    curr_patt.left,
                                    curr_patt.bottom,
                                )
                            )

                else:
                    # Save data for this normal node
                    self.graph.nodes[node_id]["x"] = x
                    self.graph.nodes[node_id]["y"] = y

            # Save ctrl pt data for top-level edges
            for edge in top_level_edges:
                data = self.decomposed_graph.edges[edge]
                gv_edge = top_level_cc_graph.get_edge(*edge)
                coords = layout_utils.get_control_points(gv_edge.attr["pos"])
                data["ctrl_pt_coords"] = coords

            if not first_small_component:
                conclude_msg()

        if first_small_component:
            conclude_msg()

        # At this point, we are now done with layout. Coordinate information
        # for nodes and edges is stored in self.graph or in the
        # subgraphs of patterns; coordinate information for patterns is stored
        # in the Pattern objects referenced in self.pattid2obj. Now we should
        # be able to make a JSON representation of this graph and move on to
        # visualizing it in the browser!

    def _rotate_from_TB_to_LR(self):
        """Rotates the graph so it flows from L -> R rather than T -> B."""
        # TODO: THIS FUNCTION IS NOW UNNECESSARY since we can now just lay out
        # the graph from L -> R from the get-go
        # Rotate and scale bounding boxes
        for cc_num in self.cc_num_to_bb.keys():
            bb = self.cc_num_to_bb[cc_num]
            self.cc_num_to_bb[cc_num] = [
                bb[1] * config.POINTS_PER_INCH,
                bb[0] * config.POINTS_PER_INCH,
            ]

        # Rotate patterns
        for patt in self.pattid2obj.values():
            # Swap height and width
            patt.width, patt.height = patt.height, patt.width
            patt.width *= config.POINTS_PER_INCH
            patt.height *= config.POINTS_PER_INCH
            # Change bounding box of the pattern.
            #
            #    _T_                  ___R___
            #   |   |       --->    T|       |B
            #  L|   |R      --->     |_______|
            #   |___|                    L
            #     B
            l, b, r, t = patt.left, patt.bottom, patt.right, patt.top
            patt.left = -t
            patt.right = -b
            patt.top = -r
            patt.bottom = -l

            # Rotate edges within this pattern
            for edge in patt.subgraph.edges:
                data = patt.subgraph.edges[edge]
                data["ctrl_pt_coords"] = layout_utils.rotate_ctrl_pt_coords(
                    data["ctrl_pt_coords"]
                )

        # Rotate normal nodes
        for node_id in self.graph.nodes:
            data = self.graph.nodes[node_id]
            data["width"], data["height"] = data["height"], data["width"]
            data["width"] *= config.POINTS_PER_INCH
            data["height"] *= config.POINTS_PER_INCH
            data["x"], data["y"] = layout_utils.rotate(data["x"], data["y"])

        # Rotate edges
        for edge in self.decomposed_graph.edges:
            data = self.decomposed_graph.edges[edge]
            data["ctrl_pt_coords"] = layout_utils.rotate_ctrl_pt_coords(
                data["ctrl_pt_coords"]
            )

    def to_dot(self, output_fp):
        """Outputs a DOT representation of the assembly graph.

        We represent patterns as Graphviz "clusters" in the DOT file; this
        means that the DOT representation will bear similarity to the fully
        uncollapsed view you'd see in MetagenomeScope.

        Parameters
        ----------
        output_fp: str
            The filepath to which this DOT file will be written.
        """
        operation_msg(f'Writing out DOT to filepath "{output_fp}"...')
        gv = layout_utils.get_gv_header()
        # we only need to bother including patterns, nodes, and edges in the
        # top level of the graph; stuff inside patterns will be included as
        # part of the top-level pattern's to_dot() :)
        for obj_coll in (self.pattid2obj, self.nodeid2obj, self.edgeid2obj):
            for obj in obj_coll.values():
                if obj.parent_id is None:
                    gv += obj.to_dot()
        gv += "}"
        with open(output_fp, "w") as fh:
            fh.write(gv)
        conclude_msg()

    def dump_dots(
        self,
        output_dir,
        graph_fn="graph.gv",
        decomposed_graph_fn="dec-graph.gv",
        full_graph_fn="full-graph.gv",
        make_pngs=True,
    ):
        """Writes out multiple versions of the graph in DOT format.

        Parameters
        ----------
        output_dir: str
            The output directory to which we will write these graphs.

        graph_fn: str or None
            Filename to give the DOT output for the uncollapsed graph. If this
            is None, we won't write out the uncollapsed graph.

        decomposed_graph_fn: str or None
            Filename to give the DOT output for the collapsed graph. If this
            is None, we won't write out the collapsed graph.

        full_graph_fn: str or None
            Filename to give the DOT output for the full graph (including all
            nodes and edges, and representing patterns as clusters). If this
            is None, we won't write out the full graph.

        make_pngs: bool
            If True, convert all of the DOT files we wrote out to PNGs; if
            False, don't. The PNG files for the uncollapsed, collapsed, and
            full graph will be named "graph.png", "dec-graph.png", and
            "full-graph.png", respectively.

        Notes
        -----
        This is a quick-and-dirty function designed for debugging. Notably, it
        uses shell=True when drawing PNGs of these graphs -- this is a security
        problem if you are running this on arbitrary user input (since
        shell=True is vulnerable to code injection). This is probably only an
        issue if you are running this on a server, and even then you can
        just... not call this function.
        """
        os.makedirs(output_dir, exist_ok=True)

        if graph_fn is not None:
            operation_msg("Writing out the uncollapsed graph...")
            g_to_write = deepcopy(self.graph)
            for n in g_to_write.nodes:
                g_to_write.nodes[n]["label"] = repr(self.nodeid2obj[n])
            gfp = os.path.join(output_dir, graph_fn)
            nx.drawing.nx_pydot.write_dot(g_to_write, gfp)
            conclude_msg()
            if make_pngs:
                operation_msg("Visualizing uncollapsed graph as a PNG...")
                png_fp = os.path.join(output_dir, "graph.png")
                subprocess.run(f"dot -Tpng {gfp} > {png_fp}", shell=True)
                conclude_msg()

        if decomposed_graph_fn is not None:
            operation_msg("Writing out the collapsed graph...")
            d_to_write = deepcopy(self.decomposed_graph)
            for n in d_to_write.nodes:
                if n in self.nodeid2obj:
                    d_to_write.nodes[n]["label"] = repr(self.nodeid2obj[n])
                else:
                    d_to_write.nodes[n]["label"] = repr(self.pattid2obj[n])
            dfp = os.path.join(output_dir, decomposed_graph_fn)
            nx.drawing.nx_pydot.write_dot(d_to_write, dfp)
            conclude_msg()
            if make_pngs:
                operation_msg("Visualizing collapsed graph as a PNG...")
                png_fp = os.path.join(output_dir, "dec-graph.png")
                subprocess.run(f"dot -Tpng {dfp} > {png_fp}", shell=True)
                conclude_msg()

        if full_graph_fn is not None:
            operation_msg("Writing out the full graph...")
            ffp = os.path.join(output_dir, full_graph_fn)
            self.to_dot(ffp)
            conclude_msg()
            if make_pngs:
                operation_msg("Visualizing full graph as a PNG...")
                png_fp = os.path.join(output_dir, "full-graph.png")
                subprocess.run(f"dot -Tpng {ffp} > {png_fp}", shell=True)
                conclude_msg()

    def _fail_if_layout_not_done(self, fn_name):
        if not self.layout_done:
            raise GraphError(
                "You need to call .layout() on this AssemblyGraph object "
                f"before calling .{fn_name}()."
            )

    def to_tsv(self, output_fp=None):
        """Writes out a TSV file describing connected component statistics.

        Parameters
        ----------
        output_fp: str or None
            Filepath to which we'll write out this TSV file.
            If this is None, just return the content of the TSV file.
        """
        output_stats = (
            "Component\tNodes\tEdges\t"
            "Bubbles\tChains\tCyclicChains\tFrayedRopes\tBipartites\n"
        )
        for cc in self.components:
            output_stats += (
                f"{cc.cc_num}\t{cc.num_full_nodes}\t{cc.num_real_edges}\t"
                f"{cc.pattern_stats.num_bubbles}\t"
                f"{cc.pattern_stats.num_chains}\t"
                f"{cc.pattern_stats.num_cyclicchains}\t"
                f"{cc.pattern_stats.num_frayedropes}\t"
                f"{cc.pattern_stats.num_bipartites}\n"
            )
        if output_fp is None:
            return output_stats
        else:
            with open(output_fp, "w") as fh:
                fh.write(output_stats)

    def _search(self, node_name_text, get_cc_map=False, get_ids=False):
        """Searches through the graph and accumulates info about nodes."""

        if not get_cc_map and not get_ids:
            # yeah yeah yeah you could write out the bitwise XNOR or whatever
            # but this is clearer imo
            raise WeirdError("Only one of these should be specified.")

        nodename2ccnum = {}
        ids = set()
        node_names_to_search = ui_utils.get_node_names(node_name_text)
        unfound_nodes = set()
        for name in node_names_to_search:
            if name in self.nodename2objs:
                for obj in self.nodename2objs[name]:
                    if get_ids:
                        ids.add(obj.unique_id)
                    if get_cc_map:
                        nodename2ccnum[obj.name] = obj.cc_num
            else:
                # Okay this node just straight up isn't in the graph
                unfound_nodes.add(name)
        ui_utils.fail_if_unfound_nodes(unfound_nodes)
        if get_ids:
            if get_cc_map:
                return (list(ids), nodename2ccnum)
            else:
                return list(ids)
        else:
            if get_cc_map:
                return nodename2ccnum
            else:
                raise WeirdError("bruh")

    def get_nodename2ccnum(self, node_name_text):
        """Returns a mapping of node names -> cc nums, given user-input text.

        Parameters
        ----------
        node_name_text: str
            Text input by the user. This should be a comma-separated list of
            node names. (But it can just be user-specified junk -- we do some
            validation to make sure it seems sane.)

        Returns
        -------
        dict
            Maps node names (strings) to their corresponding component numbers
            (ints). Note that split nodes' basenames will be "expanded" -- e.g.
            searching for a split node "40" will result in both "40-L" and
            "40-R" having entries in this. (But searching for just "40-L" will
            only give it an entry.)

        Raises
        ------
        UIError
            If the input text is malformed in some way (see
            ui_utils.get_node_names()).

            If the input text contains at least one name that does not
            correspond to a node in the graph (see
            ui_utils.fail_if_unfound_nodes()).

        Notes
        -----
        - In the future, we may want to start putting the node names included
          in these error messages in monospace (this will require fussing with
          how we create the error message toasts). One concern is that
          Bootstrap (?)'s formatting is collapsing spaces... but also, node
          names really shouldn't have spaces anyway, so probably nbd.
        """
        return self._search(node_name_text, get_cc_map=True)

    def get_node_ids(self, node_name_text):
        """Returns a list of node IDs, given user-input text.

        Parameters
        ----------
        node_name_text: str
            Text input by the user. Should be a comma-separated list of node
            names.

        Returns
        -------
        ids: list
            List of corresponding node IDs. Note that if you specify the
            basename of a split node then both its split nodes' IDs will be
            included. (However, referring directly to a single split node,
            e.g. "40-L", will only result in its ID being included.)

        Raises
        ------
        UIError
            For the same reasons as get_nodename2ccnum().
        """
        return self._search(node_name_text, get_ids=True)

    def get_node_ids_and_cc_map(self, node_name_text):
        return self._search(node_name_text, get_ids=True, get_cc_map=True)

    def get_node_names_from_ids(self, node_ids):
        # include both A-L and A-R, if both IDs are in the input
        names = []
        for i in node_ids:
            names.append(self.nodeid2obj[i].name)
        return names

    def get_region_avail_paths(self, curr_drawn_info):
        id_field = (
            config.CDI_DRAWN_NODE_IDS
            if self.node_centric
            else config.CDI_DRAWN_EDGE_IDS
        )
        if id_field not in curr_drawn_info:
            raise WeirdError(f"{id_field} not in {curr_drawn_info}?")

        avail_paths = []
        touched_paths = set()
        drawn_names = set()
        for i in curr_drawn_info[id_field]:
            if self.node_centric:
                name = self.nodeid2obj[i].basename
            else:
                name = self.edgeid2obj[i].get_userspecified_id()
            touched_paths |= self.objname2pathnames[name]
            drawn_names.add(name)

        for p in touched_paths:
            if set(self.pathname2objnames[p]).issubset(drawn_names):
                avail_paths.append(p)

        return avail_paths

    def get_neighborhood(self, node_ids, dist):
        """Returns the induced subgraph within a given distance of some nodes.

        Parameters
        ----------
        node_ids: collection of int
            IDs of nodes around which to search.

        dist: int
            We will induce the subgraph of all nodes within this many "hops"
            of any of the node_ids. So, if dist == 0, then we will just induce
            the subgraph of node_ids; if dist == 1, then we will also include
            all of their direct neighbors; and so on. Note that we ignore edge
            directionality, and treat the graph as if it were undirected.

        Returns
        -------
        subgraph, subgraph_node_ids: nx.MultiDiGraph, set of int
            The induced subgraph, computed as described above, and the set of
            all its contained node IDs (just for the sake of convenience).
        """
        # There may be more efficient ways to do this (avoiding creating an
        # an undirected view of the graph, and instead just operating directly
        # on the digraph) but this should be fine
        u = self.graph.to_undirected(as_view=True)

        # Select all nodes within distance "dist" of "node_ids"
        # NOTE: this will count split nodes towards this distance. may want to
        # change this. (https://github.com/marbl/MetagenomeScope/issues/296)
        subgraph_node_ids = set()
        for layer, ids in enumerate(nx.bfs_layers(u, node_ids)):
            if layer > dist:
                break
            subgraph_node_ids.update(ids)

        subgraph = nx.induced_subgraph(self.graph, subgraph_node_ids)
        return subgraph, subgraph_node_ids

    def get_ids_in_neighborhood(self, node_ids, dist, incl_patterns):
        """Returns the IDs of all nodes, edges, and patterns in a neighborhood.

        See get_neighborhood()'s documentation for details. The main "extra"
        thing this function does is computing which patterns should be included
        in the neighborhood; we say that a pattern is "available" for inclusion
        in the neighborhood if all of this pattern's descendant nodes and edges
        are also in the neighborhood.

        Oh also the IDs are stored in sets. in case that's relevant.
        """
        # Get nodes
        subgraph, subgraph_node_ids = self.get_neighborhood(node_ids, dist)

        # Get edges
        subgraph_edge_ids = set()
        for _, _, uid in subgraph.edges(data="uid"):
            subgraph_edge_ids.add(uid)

        # Get patterns, maybe
        subgraph_patt_ids = set()
        if incl_patterns:
            # include a pattern only if all its descendant nodes and edges are
            # included
            for pid, p in self.pattid2obj.items():
                available = True
                desc_nodes, desc_edges, desc_patts, _ = p.get_descendant_info()
                for dn in desc_nodes:
                    if dn.unique_id not in subgraph_node_ids:
                        available = False
                        break
                # NOTE: If all of the descendant nodes of a pattern are drawn,
                # then all of the descendant edges of this pattern should also
                # have been drawn. Probably??? At least for the types of
                # patterns we currently identify, I think. Just for the sake
                # of safety, we also check the edges (set lookups are fastish
                # anyway right) out of paranoia.
                for de in desc_edges:
                    if de.unique_id not in subgraph_edge_ids:
                        available = False
                        break
                if available:
                    subgraph_patt_ids.add(pid)
        return subgraph_node_ids, subgraph_edge_ids, subgraph_patt_ids

    def _to_cyjs_around_nodes(self, node_ids, dist, incl_patterns, layout_alg):
        """Produces Cytoscape.js elements only "around" certain nodes."""
        sel_node_ids, sel_edge_ids, sel_patt_ids = (
            self.get_ids_in_neighborhood(node_ids, dist, incl_patterns)
        )
        eles = []
        nodect = 0
        edgect = 0
        pattct = 0
        # TODO: this will not be as simple as just passing the layout alg
        # to the node object -- we need to perform layout on this specific
        # neighborhood and store that info in the nodes somehow.
        # When we draw entire components, the component can take care of this
        # logic; but when we draw subregions it is trickier. Probably a good
        # solution would be defining some sort of Subgraph class, analogous
        # to Component, that can manage this stuff in the same kinda way.
        if layout_alg == ui_config.LAYOUT_DOT:
            raise NotImplementedError(
                "we don't yet support drawing around nodes using dot"
            )
        for i in sel_node_ids:
            nobj = self.nodeid2obj[i]
            eles.append(nobj.to_cyjs(incl_patterns=incl_patterns))
            if nobj.split:
                nodect += 1
            else:
                nodect += 2
        for i in sel_edge_ids:
            eobj = self.edgeid2obj[i]
            eles.append(eobj.to_cyjs(incl_patterns=incl_patterns))
            if not eobj.is_fake:
                edgect += 1
        if incl_patterns:
            # if incl_patterns was False then sel_patt_ids should be empty, so
            # checking doesn't really save us much time. whatever it's clearer.
            for i in sel_patt_ids:
                eles.append(self.pattid2obj[i].to_cyjs())
            pattct = len(sel_patt_ids)
        # It is currently possible for us to draw only half of a split node
        # here (test case: velvet e. coli graph, draw around node 156 at dist
        # 1). To account for this we treat each split node as one half of a
        # full node. https://github.com/marbl/MetagenomeScope/issues/296 will
        # remove the need to do this.
        if nodect % 2 == 0:
            nodect //= 2
        else:
            nodect /= 2
        return DrawResults(
            eles,
            nodect,
            edgect,
            pattct,
            list(sel_node_ids),
            list(sel_edge_ids),
        )

    def to_cyjs(self, done_flushing):
        """Converts the graph's elements to a Cytoscape.js-compatible format.

        Parameters
        ----------
        done_flushing: dict
            Describes the draw request. The output of flush() in main.py.
            See that function for details.

        Returns
        -------
        dr: DrawResults
            Describes the stuff to be drawn. See the DrawResults definition
            in this directory for more details.

        References
        ----------
        https://dash.plotly.com/cytoscape/elements
        https://js.cytoscape.org/#notation/elements-json
        """
        draw_type = done_flushing["draw_type"]
        incl_patterns = done_flushing["patterns"]
        layout_alg = done_flushing["layout_alg"]

        if draw_type == config.DRAW_ALL:
            dr = DrawResults()
            for cc in self.components:
                dr += cc.to_cyjs(
                    incl_patterns=incl_patterns, layout_alg=layout_alg
                )

        elif draw_type == config.DRAW_CCS:
            dr = DrawResults()
            for ccn in done_flushing["cc_nums"]:
                # (self.components is an ordinary 0-indexed python list, but
                # the component numbers are 1-indexed)
                cc = self.components[ccn - 1]
                dr += cc.to_cyjs(
                    incl_patterns=incl_patterns, layout_alg=layout_alg
                )

        elif draw_type == config.DRAW_AROUND:
            dr = self._to_cyjs_around_nodes(
                done_flushing["around_node_ids"],
                done_flushing["around_dist"],
                incl_patterns,
                layout_alg,
            )

        else:
            raise WeirdError(f"Unrecognized draw type: {draw_type}")

        return dr

    def to_treemap(self, min_large_cc_ct=ui_config.MIN_LARGE_CC_COUNT):
        """Creates data describing the graph's components for use in a treemap.

        Parameters
        ----------
        min_large_cc_ct: int
            We will aggregate components with the same number of nodes together
            only if the graph contains at least this many components.
            (Or, stated another way: if the graph is small, then aggregation is
            unnecessary, so just show the full treemap to the user.)

        Returns
        -------
        names, parents, sizes, aggs: lists of (str, str, int, bool)
            The first three lists describe the names, parent names, and sizes
            (in terms of node count) of each rectangle in the treemap.

            The fourth list, aggs, describes whether or not each rectangle
            represents an aggregate of multiple components. It's useful if you
            want to apply special styles to these aggregate rectangles.

            The orders of all these lists are consistent: names[i], parents[i],
            sizes[i], and aggs[i] all describe the same i-th rectangle in the
            treemap.

            Note that the first entry of each list represents "Components", a
            rectangle describing all components in the graph. It will have no
            parent, a size equal to the total number of nodes in the graph, and
            is not considered to be an aggregate.
        """
        graph_utils.validate_multiple_ccs(self)

        cc_names = ["Components"]
        cc_parents = [""]
        cc_sizes = [self.node_ct]
        cc_aggs = [False]

        node_ct2cc_nums = defaultdict(list)
        for cc in self.components:
            node_ct2cc_nums[cc.num_full_nodes].append(cc.cc_num)

        # If the graph contains a relatively small number of components,
        # don't bother aggregating same-size components' rectangles together
        aggregate = len(self.components) >= min_large_cc_ct

        # Go in descending order of node counts: so, consider the biggest
        # component first, then the second biggest, etc.
        for node_ct in sorted(node_ct2cc_nums.keys(), reverse=True):
            cc_nums = node_ct2cc_nums[node_ct]
            names, sizes = graph_utils.get_treemap_rectangles(
                cc_nums, node_ct, aggregate=aggregate
            )
            cc_names.extend(names)
            cc_sizes.extend(sizes)
            cc_parents.extend(["Components"] * len(names))
            if len(cc_nums) > 1:
                if len(names) == 1:
                    cc_aggs.append(True)
                else:
                    cc_aggs.extend([False] * len(names))
            else:
                cc_aggs.append(False)

        return cc_names, cc_parents, cc_sizes, cc_aggs
