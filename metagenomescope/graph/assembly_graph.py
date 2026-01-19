import random
import logging
import pandas as pd
from copy import deepcopy
from collections import defaultdict
import networkx as nx
from .. import (
    parsers,
    config,
    cy_config,
    ui_config,
    color_utils,
    ui_utils,
    seq_utils,
    path_utils,
    name_utils,
    misc_utils,
)
from ..gap import Gap
from ..errors import WeirdError, GraphParsingError
from . import validators, graph_utils
from .draw_results import DrawResults
from .subgraph import Subgraph
from .component import Component
from .pattern import Pattern
from .node import Node
from .edge import Edge


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

    def __init__(self, graph_fp, agp_fp=None, flye_info_fp=None):
        """Parses the input graph file and initializes the AssemblyGraph.

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

        if self.flye_info_filename is not None:
            if self.filetype == "GFA":
                self._store_flye_info_for_gfa_nodes()
            elif self.filetype != "DOT":
                # we'll record paths later for DOT files
                logging.warning(
                    "Flye assembly info file provided. Since the input graph "
                    "is not a DOT or GFA file, we are ignoring the info file."
                )
                self.flye_info_filename = None
                self.flye_info_basename = None

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

        logger.debug("  Recording information about coverages...")
        self._record_coverages_and_lengths()
        if self.has_covs:
            total = len(self.covs) + self.missing_cov_ct
            logging.debug(
                f"  ...Done. Found {self.cov_source} coverage info! "
                f"{len(self.covs):,} / {total:,} {self.cov_source}s have a "
                f"{ui_config.COVATTR2SINGLE[self.cov_field]} given."
            )
        else:
            logger.debug(
                "  ...Done. Didn't find any node or edge coverage data, at "
                "least in a format we expect."
            )

        if self.lengths_are_approx:
            prefix = "approx. "
        else:
            prefix = ""
        logger.debug(
            f"  Computing some stats about {prefix}{self.seq_noun} "
            "sequence lengths..."
        )
        self.n50 = seq_utils.n50(self.lengths)
        self.total_seq_len = sum(self.lengths)
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
        # self.node_centric). Note that the list may also contain Gap objects
        # representing gaps specified in the path.
        self.pathname2objnamesandgaps = {}
        # Like the above, but with gaps filtered out. This is kind of silly
        # to store as its own thing but doing so avoids needing to constantly
        # recompute this sooooo
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
                self.pathname2objnamesandgaps[p] = input_paths[p]
                self.pathname2objnames[p] = [
                    n for n in input_paths[p] if type(n) is not Gap
                ]
            logger.debug(
                "  ...Done. Found "
                f"{ui_utils.pluralize(len(self.pathname2objnames), 'path')} "
                "across "
                f"{ui_utils.pluralize(len(self.ccnum2pathnames), 'component')}."
            )
        logger.info("...Done.")

    def _store_flye_info_for_gfa_nodes(self):
        df = pd.read_csv(self.flye_info_filename, sep="\t", index_col=0)
        df.rename(columns=ui_config.FLYE_INFO_COLS_TO_RENAME, inplace=True)
        fields = set(df.columns) - {"length", "graph_path"}
        # at this point, node IDs in the graph are still names - we haven't
        # called self._init_graph_objs() yet
        for n in self.graph.nodes:
            row_name = None
            if n in df.index:
                row_name = n
            elif name_utils.negate(n) in df.index:
                row_name = name_utils.negate(n)
            if row_name is not None:
                row = df.loc[row_name]
                for f in fields:
                    if (
                        f in self.graph.nodes[n]
                        and self.graph.nodes[n][f] is not None
                    ):
                        raise GraphParsingError(
                            f"Field {f} defined twice for node {n}?"
                        )
                    self.graph.nodes[n][f] = row[f]
            else:
                for f in fields:
                    self.graph.nodes[n][f] = None

    def _init_graph_objs(self):
        """Initializes Node and Edge objects for the original graph.

        This clears the NetworkX data stored for each node and edge in the
        graph (don't worry, this data isn't lost -- it's saved in the
        corresponding Node and Edge objects' .data attributes). Information
        about which of these data fields are specified for the nodes/edges is
        stored in the .extra_node_attrs and .extra_edge_attrs collections.

        Also sanity checks node names.

        And updates self.length_field, self.lengths_are_approx, and
        self.length_units.

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
        self.length_field = None
        self.lengths_are_approx = False
        self.length_units = "bp"
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

            if self.node_centric and "length" not in data:
                # at least one node doesn't have a length given, bail out
                raise WeirdError(f"Node {str_node_name} has no length?")

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

        # if this is a node-centric graph and we've made it here unscathed then
        # we know for sure that all nodes have lengths, and that these are
        # stored in a data field called "length".
        if self.node_centric:
            self.length_field = "length"

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

            # If this is an edge-centric graph, then the very first iteration
            # of this for loop will see an edge while we still have
            # self.length_field set to None. Use this first edge to determine
            # what the length field should be. Then, in all later iterations
            # of this loop, check to ensure that the other edges have this same
            # length field.
            if not self.node_centric:
                if self.length_field is None:
                    if "length" in data:
                        self.length_field = "length"
                    elif "approx_length" in data:
                        # for flye graphs that write edge lengths as e.g. "6k"
                        self.length_field = "approx_length"
                        self.lengths_are_approx = True
                    else:
                        # at least one edge doesn't have a length given, bail
                        raise WeirdError(
                            f"Edge {e[0]} -> {e[1]} has no length?"
                        )
                elif self.length_field not in data:
                    raise WeirdError(f"Edge {e[0]} -> {e[1]} has no length?")

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

        if not self.node_centric and not self.lengths_are_approx:
            # At least for now, this particular combination of things means
            # that this is an LJA DOT file, where lengths are given in
            # (K+1)-mers. See https://github.com/fedarko/metaLJA/issues/31
            self.length_units = "(K+1)-mers"

        # Now that we've seen all of these attributes, turn them from sets to
        # lists so that they have a consistent ordering. This is useful for
        # showing tables of nodes/edges in the visualization.
        # (Also, ignore attributes where the entries were all None.)
        self.extra_node_attrs = sorted(extra_node_attrs_with_atleastone_entry)
        self.extra_edge_attrs = sorted(extra_edge_attrs_with_atleastone_entry)

        # ... And, just to be extra fancy: if this is a LJA / Flye graph where
        # the edges have their own defined IDs, move these to the start of the
        # list so they're shown as the leftmost extra attr in the table.
        # Lengths should go after IDs, if present.
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "approx_length")
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "length")
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "id")

        # same deal for metacarvel edges - bsize then mean then ...
        # this is a really lazy way of doing this but i want to be safe!!!
        # plus there is no way this becomes a bottleneck lmao
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "stdev")
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "mean")
        misc_utils.move_to_start_if_in(self.extra_edge_attrs, "bsize")

        # Same deal for nodes - put the lengths as early as possible if given
        misc_utils.move_to_start_if_in(self.extra_node_attrs, "length")

        # Orientation is obvious enough that it should go last
        misc_utils.move_to_end_if_in(self.extra_node_attrs, "orientation")
        misc_utils.move_to_end_if_in(self.extra_edge_attrs, "orientation")

    def _record_coverages_and_lengths(self):
        """Stores coverage info (if given) and length info (must be given).

        You should already have called self._init_graph_objs() to have set
        self.length_field before calling this function.

        Attributes set after calling this
        ---------------------------------
        self.lengths: list of int
            List of node lengths (if self.node_centric) or edge lengths (if
            not self.node_centric).

        self.has_covs: bool
            True if there are coverages in the graph, False otherwise.
            If this is False then you should probably just ignore the remaining
            attributes described in this docstring.

        self.cov_source: str or None
            Either "node", "edge", or None, depending on where coverages are
            available in the graph. Note that this does not always match up
            with node-centricity! e.g. MetaCarvel GML graphs are node-centric
            (nodes have lengths, etc) but coverages are stored on edges as
            bundle sizes.

        self.cov_field: str or None
            This describes the node / edge (depends on self.cov_source)
            data field containing coverages.

        self.covs: list of int
            List of available coverages, analogous to self.lengths (but not
            necessarily of the same size as self.lengths, since length is a
            required field but coverage is not).

        self.has_covlens: bool
            True if there are coverages in the graph AND self.cov_source
            matches up with where lengths are available -- that is, "can
            we associate all coverage values with corresponding length
            values?" This does NOT mean that every node or edge has to have
            a defined coverage, but it does mean that all coverages can be
            related to some length. If that makes sense.

        self.name2covlen: dict of str -> (int, int)
            Maps node names or user-specified edge IDs to a (cov, len) tuple.
            Notes:
            - This excludes nodes or edges that don't have defined coverages.
            - If the input graph included two copies of each sequence (e.g.
              node 123 and node -123) then both copies will be represented here
              (assuming that both had a defined coverage). That said, remember
              that we are calling this function BEFORE the graph decomposition
              stuff, so we don't have to worry about fake edges or split nodes
              messing with the values here.

        self.missing_cov_ct: int
            Lists the number of nodes or edges (depending on self.cov_source)
            that do not have a defined coverage. As before, this is computed
            before the decomposition, so like yeah of course fake edges don't
            have a coverage but also they won't be described in this count
            because that would be silly.

        self.possible_covlen_ct: int
            Equal to len(self.lengths). Basically, this is a way of saying
            "if every possible node or edge in the input graph had an
            associated coverage, how big would self.name2covlen be?"

        Anyway if there are coverages then we can show coverage plots! yay.

        Notes
        -----
        - This prioritizes node coverages over edge coverages, if both are
          given. As of writing that should only happen in Velvet output, among
          all the graph filetypes we support, so I think that's fine. (Like we
          totally COULD add support for switching between plots of node and
          edge coverages but is the juice worth the squeeze? eh.)

        - In theory GFA files can have RC/FC/KC tags for links*, but i don't
          think i've ever seen that in a GFA file. Gfapy doesn't even seem to
          support this (segments have a .coverage() method, links don't, even
          if you add in a link with an RC tag). Anyway if desired we can add
          support for this.
          * https://github.com/GFA-spec/GFA-spec/blob/master/GFA1.md

        - We COULD do this in the for-loops in self._init_graph_objs(), which
          would save us the time spent iterating through the nodes / edges
          again, but that would be tricky and annoying and it's easier to split
          things up this way. self._init_graph_objs() probably does too much as
          it is.

        - Similarly, storing self.name2covlen is kind of memory inefficient,
          right? But I am willing to trade a bit of inefficiency for a lot of
          safety in not having to repeatedly scan through the graph after
          decomposition and be like ummm is this a split node or is it a ...
        """
        self.lengths = []
        self.has_covs = False
        self.cov_source = None
        self.cov_field = None
        self.covs = []
        self.has_covlens = False
        self.name2covlen = {}
        self.missing_cov_ct = 0

        # Do the nodes have coverages?
        # NOTE: as of jan 2026 no parsers currently output "depth" info for
        # nodes. let's include it in the tuple below anyway just to be safe
        for ncfield in ("cov", "depth"):
            if ncfield in self.extra_node_attrs:
                self.cov_source = "node"
                self.cov_field = ncfield
                break

        # Or... do the edges have coverages?
        if self.cov_source is None:
            for ecfield in ("bsize", "cov", "kp1mer_cov", "multiplicity"):
                if ecfield in self.extra_edge_attrs:
                    self.cov_source = "edge"
                    self.cov_field = ecfield
                    break

        # If there are coverages, record them!
        if self.cov_source is not None:
            if self.cov_source == "node":
                id2obj = self.nodeid2obj
            else:
                id2obj = self.edgeid2obj

            for obj in id2obj.values():
                if self.cov_field in obj.data:
                    cov = obj.data[self.cov_field]
                    if cov is not None:
                        self.covs.append(cov)
                        continue
                # If this node/edge didn't have the cov field at all in its
                # data dict - or if it had it, but the value was None - then
                # ignore
                self.missing_cov_ct += 1
            if len(self.covs) > 0:
                self.has_covs = True

        # We know that all nodes or edges (depending on the input filetype)
        # should have lengths. So, we can figure out if we can pair coverage x
        # length info in a scatterplot by comparing the graph's node-centricity
        # (not a word) with where the coverages are coming from. (I think the
        # only time self.has_covs will be True but self.has_covlens will be
        # False is for MetaCarvel GMLs, where edges have bsizes but no
        # "lengths".
        if self.has_covs:
            if self.cov_source == "node":
                self.has_covlens = self.node_centric
            else:
                self.has_covlens = not self.node_centric

        if self.has_covlens:
            for obj in id2obj.values():
                if self.cov_field in obj.data:
                    ocov = obj.data[self.cov_field]
                    if ocov is not None:
                        olen = obj.data[self.length_field]
                        if olen is None:
                            # should never happen, since we already should have
                            # verified that all nodes or all edges have lengths
                            raise WeirdError(
                                f"{obj} has no {self.length_field}"
                            )
                        if self.node_centric:
                            key = obj.name
                        else:
                            key = obj.get_userspecified_id()
                        self.name2covlen[key] = (ocov, olen)

        if self.node_centric:
            id2obj = self.nodeid2obj
        else:
            id2obj = self.edgeid2obj
        for obj in id2obj.values():
            self.lengths.append(obj.data[self.length_field])
        self.possible_covlen_ct = len(self.lengths)

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

    def get_component_node_cts(self):
        """Returns a list of "full" node counts in each component.

        That is, this treats each pair of split nodes A-L and A-R as a single
        node, but also treats reverse-complementary nodes separately (so, if a
        component contains both node A and node -A, then this will count as two
        nodes). And the corollary of that is that if a component has
        A-L, A-R, -A-L, and -A-R, then it contains just two nodes.

        So like this is what we want to show the user - node splitting won't
        impact these results.
        """
        return [cc.num_full_nodes for cc in self.components]

    def get_component_edge_cts(self):
        """Returns a list of "real" edge counts in each component."""
        return [cc.num_real_edges for cc in self.components]

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
            nodes = []
            edges = []
            patts = []
            for nid in cc:
                if self.is_pattern(nid):
                    patt = self.pattid2obj[nid]
                    # get_descendant_info() goes through ALL descendants,
                    # not just children. so if we see a collapsed pattern node
                    # then here we get all of its children, grandchildren, ...
                    #
                    # Also! note that calling patt.get_descendant_info()
                    # includes "patt" in the output "ppatts" list. So, no
                    # need to run patts.append(nid) or something.
                    pnodes, pedges, ppatts, _ = patt.get_descendant_info()
                    for n in pnodes:
                        nodes.append(n)
                    for e in pedges:
                        edges.append(e)
                    for p in ppatts:
                        patts.append(p)
                else:
                    # this is just an ordinary top-level node
                    nodes.append(self.nodeid2obj[nid])
                # Record all of the top-level edges in this component by
                # looking at the outgoing edges of each "node", whether it's a
                # real or collapsed-pattern node. (Don't worry, this includes
                # parallel edges.)
                for src_id, tgt_id, data in self.decomposed_graph.out_edges(
                    nid, data=True
                ):
                    edges.append(self.edgeid2obj[data["uid"]])
            components.append(
                Component(self._get_unique_id(), nodes, edges, patts)
            )

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
            # remember that self.pathname2objnames[p] does not contain Gaps,
            # so no need to worry about those here
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

    def get_ids_in_neighborhood(self, node_ids, dist, draw_settings):
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
        if ui_utils.show_patterns(draw_settings):
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

    def _to_cyjs_around_nodes(self, node_ids, dist, draw_settings, layout_alg):
        """Produces Cytoscape.js elements only "around" certain nodes."""
        sel_node_ids, sel_edge_ids, sel_patt_ids = (
            self.get_ids_in_neighborhood(node_ids, dist, draw_settings)
        )
        # NOTE: in theory, if a user draws around nodes multiple times then
        # we will just keep creating new subgraph ids. however, since diff
        # versions of mgsc on diff workers may not share memory, we may reuse
        # IDs here. I think this is fine, but if we really want to keep things
        # 100% stateless we can just use a constant id here, or create a uuid,
        # etc
        sid = self._get_unique_id()
        sg = Subgraph(
            sid,
            f"Subgraph{sid}",
            [self.nodeid2obj[i] for i in sel_node_ids],
            [self.edgeid2obj[i] for i in sel_edge_ids],
            [self.pattid2obj[i] for i in sel_patt_ids],
        )
        return sg.to_cyjs(
            draw_settings=draw_settings, layout_alg=layout_alg, report_ids=True
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
        draw_settings = done_flushing["draw_settings"]
        layout_alg = done_flushing["layout_alg"]

        if draw_type == config.DRAW_ALL:
            dr = DrawResults()
            for cc in self.components:
                dr += cc.to_cyjs(
                    draw_settings=draw_settings, layout_alg=layout_alg
                )

        elif draw_type == config.DRAW_CCS:
            dr = DrawResults()
            for ccn in done_flushing["cc_nums"]:
                # (self.components is an ordinary 0-indexed python list, but
                # the component numbers are 1-indexed)
                cc = self.components[ccn - 1]
                dr += cc.to_cyjs(
                    draw_settings=draw_settings, layout_alg=layout_alg
                )

        elif draw_type == config.DRAW_AROUND:
            dr = self._to_cyjs_around_nodes(
                done_flushing["around_node_ids"],
                done_flushing["around_dist"],
                draw_settings,
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
