import math
import json
import os
from copy import deepcopy
from operator import itemgetter
from collections import deque
import numpy
import networkx as nx
import pygraphviz


from .. import parsers, config, layout_utils
from ..msg_utils import operation_msg, conclude_msg
from ..errors import GraphParsingError, WeirdError
from . import validators
from .pattern import StartEndPattern, Pattern
from .node import Node
from .edge import Edge


class AssemblyGraph(object):
    """Representation of an input assembly graph.

    This contains information about the top-level structure of the graph:
    including nodes, edges, and connected components.

    In fancy object-oriented programming terminology, this class is a
    "composition" with a NetworkX MultiDiGraph. This really just means that,
    rather than subclassing nx.MultiDiGraph, this class just contains an
    instance of nx.MultiDiGraph (self.graph) of which we make use.

    CODELINK: This "composition" paradigm was based on this post:
    https://www.thedigitalcatonline.com/blog/2014/08/20/python-3-oop-part-3-delegation-composition-and-inheritance/
    """

    def __init__(
        self,
        filename,
        max_node_count=config.MAXN_DEFAULT,
        max_edge_count=config.MAXE_DEFAULT,
        patterns=True,
    ):
        """Parses the input graph file and initializes the AssemblyGraph.

        After you create a graph, you should usually call the process() method
        to prepare the graph for visualization (scaling nodes/edges,
        identifying patterns, etc.).

        Parameters
        ----------
        filename: str
            Path to the assembly graph to be visualized.

        max_node_count: int
            We won't visualize connected components containing more nodes than
            this.

        max_edge_count: int
            Like max_node_count, but for edges.

        patterns: bool
            If True, identify & highlight structural patterns; if False, don't.
        """
        self.filename = filename
        self.max_node_count = max_node_count
        self.max_edge_count = max_edge_count
        self.find_patterns = patterns

        self.basename = os.path.basename(self.filename)
        # NOTE: Ideally we'd just return this along with the graph from
        # parsers.parse(), but uhhhh that will make me refactor
        # like 20 tests and I don't want to do that ._.
        self.filetype = parsers.sniff_filetype(self.filename)
        self.graph = parsers.parse(self.filename)

        # Remove nodes/edges in components that are too large to lay out.
        self.num_too_large_components = 0
        self.remove_too_large_components()

        # These store Node, Edge, and Pattern objects. We still use the
        # NetworkX graph objects to do things like identify connected
        # components, find all edges incident on a node, etc., but data about
        # these objects (both user-provided [e.g. "length"] and internal [e.g.
        # "width"] data) will primarily be stored in these objects.
        self.nodeid2obj = {}
        self.edgeid2obj = {}
        self.pattid2obj = {}

        # "Extra" data for nodes / edges -- e.g. GC content, coverage,
        # multiplicity, ... -- will be updated based on what we see in
        # self.init_graph_objs().
        self.extra_node_attrs = set()
        self.extra_edge_attrs = set()

        # Populate self.nodeid2obj and self.edgeid2obj, and re-labels nodes in
        # the graph (and adds an "id" attribute for edges in the graph). This
        # way, we can easily associate nodes and edges with their corresponding
        # objects' unique IDs.
        self.init_graph_objs()

        # Number of nodes in the graph, including patterns and duplicate nodes.
        # Used for assigning new unique node IDs.
        self.num_nodes = len(self.graph)

        # Records the bounding boxes of each component in the graph. Indexed by
        # component number (1-indexed). (... We could also store this as an
        # array, but due to the whole component skipping stuff that sounds like
        # asking for trouble. Plus it's not like this will take up a ton of
        # memory, I think.)
        self.cc_num_to_bb = {}

        # Each entry in these structures will be a Pattern (or subclass).
        # NOTE that these patterns will only be "represented" in
        # self.decomposed_graph; self.graph represents the literal graph
        # structure as initially parsed (albeit with some duplicate nodes added
        # in for convenience's sake, maybe).
        self.chains = []
        self.cyclic_chains = []
        self.bubbles = []
        self.frayed_ropes = []

        # Holds the top-level decomposed graph. All of the original nodes /
        # edges in the graph are accounted for within this graph in some way --
        # they're either present within the actual graph (i.e. they were not
        # collapsed into patterns), or they are present within the subgraph of
        # a pattern (which may in turn be a node in the top-level graph or
        # within the subgraph of another pattern, etc.)
        self.decomposed_graph = deepcopy(self.graph)

        # Node/edge scaling is done *before* pattern detection, so duplicate
        # nodes/edges created during pattern detection shouldn't influence
        # relative scaling stuff.
        operation_msg("Scaling nodes based on lengths...")
        self.scale_nodes()
        conclude_msg()

        self.scale_edges()

        # TODO: During the April 2023 refactor, WE ARE HERE. Need to update
        # these functions to set these internal attributes (width, height,
        # relative_length, ...) as attributes of Node/Edge attributes --
        # blessedly, leaving user-provide Node/Edge data separate.
        if self.find_patterns:
            operation_msg("Running hierarchical pattern decomposition...")
            self.hierarchically_identify_patterns()
            conclude_msg()

        # Defer this until after we do pattern decomposition, to account for
        # split nodes. (At this point we have already called scale_nodes() --
        # so the presence of split nodes shouldn't change how other nodes in
        # the graph are scaled.)
        # TODO -- update compute_node_dimensions() to run on the decomposed
        # graph, not the original graph
        self.compute_node_dimensions()

        operation_msg("Laying out the graph...", True)
        self.layout()
        operation_msg("...Finished laying out the graph.", True)

        operation_msg("Rotating and scaling things as needed...")
        self.rotate_from_TB_to_LR()
        conclude_msg()

    def init_graph_objs(self):
        """Initializes Node and Edge objects for the original graph.

        Also, clears the NetworkX data stored for each node and edge in the
        graph (don't worry, this data isn't lost -- it's saved in the
        corresponding Node and Edge objects' .data attributes).

        Finally, this relabels nodes in the graph to match their corresponding
        Node object's unique_id; and adds an "id" attribute to edges' NetworkX
        data that matches their corresponding Edge object's unique_id.

        Notes
        -----
        We may add more Node and Edge objects as we perform pattern detection
        and node splitting. That will be done separately; this method just
        establishes a "baseline."
        """
        oldid2uniqueid = {}
        for ni, n in enumerate(self.graph.nodes):
            data = copy.deepcopy(self.graph.nodes[n])
            self.nodeid2obj[ni] = Node(ni, data)
            self.extra_node_attrs |= set(data.keys())
            # Remove node data from the graph (we've already saved it in the
            # Node object's .data attribute).
            self.graph.nodes[n].clear()
            # We'll re-label nodes in the graph, to make it easy to associate
            # them with their corresponding Node objects.
            oldid2uniqueid[n] = ni

        nx.relabel_nodes(self.graph, oldid2uniqueid, copy=False)

        for ei, e in enumerate(self.graph.edges(data=True, keys=True)):
            # e is a 4-tuple of (source ID, sink ID, key, data dict)
            self.edgeid2obj[ni] = Edge(ei, e[0], e[1], copy.deepcopy(e[3]))
            self.extra_edge_attrs |= set(e[2].keys())
            # Remove edge data from the graph.
            self.graph.edges[e[0], e[1], e[2]].clear()
            # Edges in NetworkX don't really have "IDs," but we can use the
            # (now-cleared) data dict in the graph to store their ID. This will
            # make it easy to associate this edge with its Edge object.
            self.graph.edges[e[0], e[1], e[2]]["id"] = ei

    def remove_too_large_components(self):
        # We convert the WCC collection to a list so that even if we alter the
        # graph in the middle of the loop we don't risk the collection being
        # messed up
        wccs = list(nx.weakly_connected_components(self.graph))
        num_wccs = len(wccs)
        for cc_node_ids in wccs:
            num_nodes = len(cc_node_ids)
            num_edges = len(self.graph.subgraph(cc_node_ids).edges)
            if (
                num_nodes > self.max_node_count
                or num_edges > self.max_edge_count
            ):
                self.graph.remove_nodes_from(cc_node_ids)
                self.num_too_large_components += 1
                operation_msg(
                    (
                        f"Ignoring a component ({num_nodes:,} nodes, "
                        f"{num_edges:,} edges): exceeds -maxn or -maxe."
                    ),
                    True,
                )

        if self.num_too_large_components == num_wccs:
            raise ValueError(
                "All components were too large to lay out. Try increasing the "
                "-maxn/-maxe parameters, or reducing the size of the graph."
            )

    def get_new_node_id(self):
        """Returns an int guaranteed to be usable as a unique new node ID."""
        # this is what they pay me the big bucks for, folks. this is home-grown
        # organic computer science right here
        new_id = self.num_nodes
        self.num_nodes += 1
        return new_id

    def add_pattern(self, member_node_ids, pattern_type):
        """Adds a pattern composed of a list of node IDs to the decomposed
        DiGraph, and removes its children from the decomposed DiGraph.

        Routes incoming edges to nodes within this pattern (from outside of the
        pattern) to point to the pattern node, and routes outgoing edges from
        nodes within this pattern (to outside of the pattern) to originate from
        the pattern node.

        Returns a new Pattern object.
        """
        pattern_id = self.get_new_node_id()

        # Get incoming edges to this pattern
        in_edges = self.decomposed_graph.in_edges(member_node_ids)
        p_in_edges = list(
            filter(lambda e: e[0] not in member_node_ids, in_edges)
        )
        # Get outgoing edges from this pattern
        out_edges = self.decomposed_graph.out_edges(member_node_ids)
        p_out_edges = list(
            filter(lambda e: e[1] not in member_node_ids, out_edges)
        )
        # Add this pattern to the decomposed graph, with the same in/out
        # nodes as in the subgraph of this pattern's nodes
        self.decomposed_graph.add_node(pattern_id, pattern_type=pattern_type)
        for e in p_in_edges:
            edge_data = self.decomposed_graph.edges[e]
            self.decomposed_graph.add_edge(e[0], pattern_id, **edge_data)
        for e in p_out_edges:
            edge_data = self.decomposed_graph.edges[e]
            self.decomposed_graph.add_edge(pattern_id, e[1], **edge_data)

        # Get the "induced subgraph" of just the first-level child nodes. Used
        # for layout. We call .copy() because otherwise the node removal stuff
        # from self.decomposed_graph will also remove nodes from subgraph.
        subgraph = self.decomposed_graph.subgraph(member_node_ids).copy()

        # Remove the children of this pattern from the decomposed DiGraph
        # (they're not gone forever, of course! -- we should hold on a
        # reference to everything, albeit sort of circuitously -- so the
        # topmost pattern has a reference to its child nodes' and patterns'
        # IDs, and these child pattern(s) will have references to their
        # children node/pattern IDs, etc.)
        self.decomposed_graph.remove_nodes_from(member_node_ids)

        p = Pattern(pattern_id, pattern_type, member_node_ids, subgraph, self)
        return p

    def add_bubble(self, member_node_ids, start_node_id, end_node_id):
        """Adds a bubble composed of a list of node IDs to the decomposed
        DiGraph, and removes its children from the decomposed DiGraph.

        Additionally, this will check to see if the nodes corresponding to
        start_node_id and end_node_id are themselves collapsed patterns
        (for now they can only be other bubbles, but in theory any pattern with
        a single starting and end node is kosher -- e.g. chains, cyclic
        chains).

        If the start node is already a collapsed pattern, this will
        duplicate the end node of that pattern within this new bubble and
        create a link accordingly. Similarly, if the end node is already a
        collapsed pattern, this'll duplicate the start node of that bubble
        in the new bubble.

        Returns a new StartEndPattern object.
        """
        pattern_id = self.get_new_node_id()
        self.decomposed_graph.add_node(pattern_id, pattern_type="bubble")

        if "pattern_type" in self.decomposed_graph.nodes[start_node_id]:
            # In the actual graph, create a new node that'll serve as the
            # "duplicate" of this node within the new pattern we're creating.
            # Shares all data, and holds the outgoing edges of the original
            # node -- all of these outgoing edges should be _within_ this new
            # pattern.

            # Get end node of the starting pattern, and duplicate it
            end_node_to_dup = self.pattid2obj[start_node_id].get_end_node()
            data = self.graph.nodes[end_node_to_dup]
            new_node_id = self.get_new_node_id()
            self.graph.add_node(new_node_id, is_dup=True, **data)

            # Duplicate outgoing edges of the duplicated node in the original
            # graph
            for edge in list(self.graph.out_edges(end_node_to_dup)):
                edge_data = self.graph.edges[edge]
                edge_data["orig_src"] = new_node_id
                self.graph.add_edge(new_node_id, edge[1], **edge_data)
                self.graph.remove_edge(end_node_to_dup, edge[1])

            # Duplicate outgoing edges of the duplicated node in the decomposed
            # graph
            for edge in list(self.decomposed_graph.out_edges(start_node_id)):
                edge_data = self.decomposed_graph.edges[edge]
                edge_data["orig_src"] = new_node_id
                self.decomposed_graph.add_edge(
                    new_node_id, edge[1], **edge_data
                )
                self.decomposed_graph.remove_edge(start_node_id, edge[1])
                # NOTE: Removing edges from the decomposed graph should be
                # unnecessary, since edge[1] and all of the other nodes within
                # this pattern (ignoring start_node_id) will be removed from
                # the decomposed graph at the end of this function
                # self.decomposed_graph.remove_edge(start_node_id, edge[1])

            # In the normal graph, link the node and its duplicate
            self.graph.add_edge(
                end_node_to_dup,
                new_node_id,
                is_dup=True,
                orig_src=end_node_to_dup,
                orig_tgt=new_node_id,
            )
            # In the decomposed graph, link the starting pattern with the
            # curr pattern.
            self.decomposed_graph.add_edge(
                start_node_id,
                pattern_id,
                is_dup=True,
                orig_src=end_node_to_dup,
                orig_tgt=new_node_id,
            )

            member_node_ids.remove(start_node_id)
            member_node_ids.append(new_node_id)
            start_node_id = new_node_id

        if "pattern_type" in self.decomposed_graph.nodes[end_node_id]:
            # Get start node of the ending pattern, and duplicate it
            start_node_to_dup = self.pattid2obj[end_node_id].get_start_node()
            data = self.graph.nodes[start_node_to_dup]
            new_node_id = self.get_new_node_id()
            self.graph.add_node(new_node_id, is_dup=True, **data)

            # Duplicate incoming edges of the duplicated node
            for edge in list(self.graph.in_edges(start_node_to_dup)):
                edge_data = self.graph.edges[edge]
                edge_data["orig_tgt"] = new_node_id
                # Update the original nodes in the plain graph to point to
                # the new duplicate. And update the nodes in the decomposed
                # graph -- they'll be removed soon anyway, but we do this
                # so that the subgraph is accurate)
                self.graph.add_edge(edge[0], new_node_id, **edge_data)
                self.graph.remove_edge(edge[0], start_node_to_dup)
                # See comment in the above block (for replacing the start node)
                # about this
                # self.decomposed_graph.remove_edge(edge[0], end_node_id)

            for edge in list(self.decomposed_graph.in_edges(end_node_id)):
                edge_data = self.decomposed_graph.edges[edge]
                edge_data["orig_tgt"] = new_node_id
                self.decomposed_graph.add_edge(
                    edge[0], new_node_id, **edge_data
                )
                self.decomposed_graph.remove_edge(edge[0], end_node_id)

            self.graph.add_edge(
                new_node_id,
                start_node_to_dup,
                is_dup=True,
                orig_src=new_node_id,
                orig_tgt=start_node_to_dup,
            )
            self.decomposed_graph.add_edge(
                pattern_id,
                end_node_id,
                is_dup=True,
                orig_src=new_node_id,
                orig_tgt=start_node_to_dup,
            )

            member_node_ids.remove(end_node_id)
            member_node_ids.append(new_node_id)
            end_node_id = new_node_id

        # NOTE TODO abstract between this and prev func.
        # Get incoming edges to this pattern
        in_edges = self.decomposed_graph.in_edges(member_node_ids)
        p_in_edges = list(
            filter(lambda e: e[0] not in member_node_ids, in_edges)
        )
        # Get outgoing edges from this pattern
        out_edges = self.decomposed_graph.out_edges(member_node_ids)
        p_out_edges = list(
            filter(lambda e: e[1] not in member_node_ids, out_edges)
        )
        for e in p_in_edges:
            edge_data = self.decomposed_graph.edges[e]
            self.decomposed_graph.add_edge(e[0], pattern_id, **edge_data)
        for e in p_out_edges:
            edge_data = self.decomposed_graph.edges[e]
            self.decomposed_graph.add_edge(pattern_id, e[1], **edge_data)

        subgraph = self.decomposed_graph.subgraph(member_node_ids).copy()

        # Remove the children of this pattern from the decomposed DiGraph.
        self.decomposed_graph.remove_nodes_from(member_node_ids)

        p = StartEndPattern(
            pattern_id,
            "bubble",
            member_node_ids,
            start_node_id,
            end_node_id,
            subgraph,
            self,
        )
        return p

    def hierarchically_identify_patterns(self):
        """Run all of our pattern detection algorithms on the graph repeatedly.

        This is the main Fancy Thing we do, besides layout.
        """
        while True:
            # Run through all of the pattern detection methods on all of the
            # top-level nodes (or node groups) in the decomposed graph.
            # Keep doing this until we get to a point where we've run every
            # pattern detection method on the graph, and nothing new has been
            # found.
            something_collapsed = False

            # You could switch the order of this tuple up in order to
            # change the "precedence" of pattern detection, if desired.
            # I think identifying bulges and chains first makes sense, if
            # nothing else.
            for collection, validator, ptype in (
                (self.bubbles, validators.is_valid_bulge, "bubble"),
                (self.chains, validators.is_valid_chain, "chain"),
                (self.bubbles, validators.is_valid_bubble, "bubble"),
                (
                    self.cyclic_chains,
                    validators.is_valid_cyclic_chain,
                    "cyclicchain",
                ),
            ):
                # We sort the nodes in order to make this deterministic
                # (I doubt the extra time cost from sorting will be a big deal)
                candidate_nodes = sorted(list(self.decomposed_graph.nodes))
                while len(candidate_nodes) > 0:
                    n = candidate_nodes[0]
                    validator_results = validator(self.decomposed_graph, n)
                    if validator_results:

                        # TODO do this for all patterns that have these attrs
                        # defined, not just bubbles. (Really, everything except
                        # for frayed ropes, which are top-level-only patterns.)
                        if ptype == "bubble":
                            # There is a start and end node in this pattern
                            # that we may want to duplicate. See issue #84 on
                            # GitHub for lots and lots of details.
                            p = self.add_bubble(
                                validator_results.nodes,
                                validator_results.start_node,
                                validator_results.end_node,
                            )
                        else:
                            p = self.add_pattern(
                                validator_results.nodes, ptype
                            )

                        collection.append(p)
                        candidate_nodes.append(p.pattern_id)
                        self.pattid2obj[p.pattern_id] = p
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
                        # If the pattern was invalid, we still need to
                        # remove n
                        candidate_nodes.remove(n)
            if not something_collapsed:
                # We didn't collapse anything... so we're done here! We can't
                # do any more.
                break

        # Now, identify frayed ropes (and other "top-level only" patterns, if
        # desired). TODO.

        # Now that we're done here, go through all the nodes and edges in the
        # top level of the graph and record that they don't have a parent
        # pattern
        for node_id in self.decomposed_graph.nodes:
            if not self.is_pattern(node_id):
                self.graph.nodes[node_id]["parent_id"] = None
        for edge in self.decomposed_graph.edges:
            self.decomposed_graph.edges[edge]["parent_id"] = None

    def get_node_lengths(self):
        lengths = {}
        for ni, n in self.nodeid2obj.items():
            if n.split is None and "length" in n.data:
                lengths[ni] = n.data["length"]
        return lengths

    def scale_nodes_all_uniform(self):
        for node in self.nodeid2obj.values():
            node.relative_length = 0.5
            node.longside_proportion = config.MID_LONGSIDE_PROPORTION

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
            self.scale_nodes_all_uniform()
        else:
            node_length_values = node_lengths.values()
            min_len = min(node_length_values)
            max_len = max(node_length_values)

            # bail out if all nodes have equal lengths
            if min_len == max_len:
                self.scale_nodes_all_uniform()
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

    def compute_node_dimensions(self):
        r"""Adds height and width attributes to each node in the graph.

        It is assumed that scale_nodes() has already been called; otherwise,
        this will be unable to access the relative_length and
        longside_proportion node attributes, which will cause a KeyError.

        This only covers "bottom-level" nodes -- i.e. patterns are not assigned
        dimensions, since those should be scaled based on the bounding box
        needed to contain their child elements. However, "duplicate" nodes
        should be assigned dimensions, since for all intents and purposes
        they're "real". (It may be possible to speed this up slightly by only
        duplicating data for these nodes after doing scaling, etc., but I doubt
        that the time savings there will be that useful in most cases.)

        It is very important to understand that here, "height" and "width"
        refer to nodes' positions in the graph when laid out from top to
        bottom:
         __
        |  |
        |  |
         \/

         |                  ___         ___
         |           , not |   \       |   \    :(
         V                 |___/  ---> |___/
         __
        |  |
        |  |
         \/

        Although Graphviz does accept a "rankdir" graph attribute that can be
        used to make graph drawings flow from left to right, rather than from
        top to bottom, this attribute is not respected when *just* laying out
        the graph. At least to my knowledge. So unfortunately we have to do the
        rotation ourselves. Therefore, in the visualization interface shown to
        MetagenomeScope users, the width and height of each node are really the
        opposite from what we store here.
        """
        for node in self.graph.nodes:
            data = self.graph.nodes[node]
            area = config.MIN_NODE_AREA + (
                data["relative_length"] * config.NODE_AREA_RANGE
            )
            # Again, in the interface the height will be the width and the
            # width will be the height
            data["height"] = area ** data["longside_proportion"]
            data["width"] = area / data["height"]

    def get_edge_weight_field(
        self, field_names=["bsize", "multiplicity", "cov", "kmer_cov"]
    ):
        """Returns the name of the edge weight field this graph has.

        If the graph does not have any edge weight fields, or if only some
        edges have an edge weight field, returns None.

        If there are multiple edge weight fields, this raises a
        GraphParsingError.

        The list of field names corresponding to "edge weights" is
        configurable via the field_names parameter. You should verify (in the
        assembly graph parsers) that these fields correspond to positive
        numbers.

        Notes
        -----
        - This entire function should be removed, eventually, in favor of
          letting the user dynamically choose how to adjust edge weights in the
          browser.

        - It should be possible to merge this function with init_graph_objs();
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
            """Assigns "normal" attributes to each Edge object in edges."""
            for edge in edges:
                edge.is_outlier = 0
                edge.relative_weight = 0.5

        ew_field = self.get_edge_weight_field()
        if ew_field is not None:
            operation_msg("Scaling edges based on weights...")
            real_edges = []
            weights = []
            for edge in self.edgeid2obj.values():
                if not edge.is_fake:
                    real_edges.append(edge)
                    weights.append(edge.data[ew_field])
                else:
                    raise WeirdError(
                        "Duplicate edges shouldn't exist in the graph yet."
                    )

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
                for edge in real_edges:
                    if not edge.is_fake:
                        edge.is_outlier = 0
                        non_outlier_edges.append(edge)
                        ew = edge.data[ew_field]
                        non_outlier_edge_weights.append(ew)
                    else:
                        raise WeirdError(
                            "Duplicate edges shouldn't exist in the graph yet."
                        )

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
        if node_id >= self.num_nodes or node_id < 0:
            raise ValueError("Node ID {} seems out of range.".format(node_id))
        return node_id in self.pattid2obj

    def get_connected_components(self):
        """Returns a list of 3-tuples, where the first element in each tuple is
        a set of (top-level) node IDs within this component in the decomposed
        graph, the second element is the total number of nodes (not
        counting collapsed patterns, but including nodes within patterns and
        also including duplicate nodes) within this component, and the third
        element is the total number of edges within this component.

        Components are sorted in descending order by number of nodes first,
        then number of edges, then number of patterns. This is a simple-ish way
        of highlighting the most "interesting" components -- e.g. a component
        with 1 node with an edge to itself is more "interesting" than a
        component with just 1 node and no edges.
        """
        ccs = list(nx.weakly_connected_components(self.decomposed_graph))
        # Set up as [[zero-indexed cc pos, node ct, edge ct, pattern ct], ...]
        # Done this way to make sorting components easier.
        # This paradigm based roughly on what's done here:
        # https://docs.python.org/3.3/howto/sorting.html#operator-module-functions
        indices_and_cts = [[n, 0, 0, 0] for n in range(len(ccs))]
        for i, cc in enumerate(ccs):
            for node_id in cc:
                if self.is_pattern(node_id):
                    # Add the pattern's node, edge, and pattern counts to this
                    # component's node, edge, and pattern counts.
                    counts = self.pattid2obj[node_id].get_counts(self)
                    indices_and_cts[i][1] += counts[0]
                    indices_and_cts[i][2] += counts[1]
                    # (Increase the pattern count by 1, to account for this
                    # pattern itself.)
                    indices_and_cts[i][3] += counts[2] + 1
                else:
                    indices_and_cts[i][1] += 1
                # Record all of the top-level edges in this component by
                # looking at the outgoing edges of each "node", whether it's a
                # real or collapsed-pattern node.
                # We could also create the induced subgraph of this component's
                # nodes (in "cc") and then count the number of edges there, but
                # I think this is more efficient.
                indices_and_cts[i][2] += len(
                    self.decomposed_graph.edges(node_id)
                )

        sorted_indices_and_cts = sorted(
            indices_and_cts, key=itemgetter(1, 2, 3), reverse=True
        )
        # Use the first item within sorted_indices_and_cts (representing the
        # zero-indexed position of that component in the "ccs" list defined at
        # the start of this function) to produce a list containing the node IDs
        # in each component, sorted in the order used in
        # sorted_indices_and_cts.
        #
        # I can't help but think this approach is overly complicated, but also
        # christ I am so tired. If you're reading this comment in 2021 then
        # friend I am so jealous of you for not being in 2020 any more. If you
        # wanna use all the free time you have in 2021 to submit a PR and make
        # this function prettier, us 2020 denizens would welcome that.
        return [(ccs[t[0]], t[1], t[2]) for t in sorted_indices_and_cts]

    def layout(self):
        """Lays out the graph's components, handling patterns specially."""
        # Do layout one component at a time.
        # (We don't bother checking for skipped components, since we should
        # have already called self.remove_too_large_components().)
        first_small_component = False
        for cc_i, cc_tuple in enumerate(
            self.get_connected_components(), self.num_too_large_components + 1
        ):
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
                    self.pattid2obj[node_id].set_cc_num(self, cc_i)
                    # Lay out the pattern in isolation (could involve multiple
                    # layers, since patterns can contain other patterns).
                    self.pattid2obj[node_id].layout(self)
                    height = self.pattid2obj[node_id].height
                    width = self.pattid2obj[node_id].width
                    shape = self.pattid2obj[node_id].shape
                else:
                    data = self.graph.nodes[node_id]
                    data["cc_num"] = cc_i
                    height = data["height"]
                    width = data["width"]
                    shape = config.NODE_ORIENTATION_TO_SHAPE[
                        data["orientation"]
                    ]
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
                            data[
                                "ctrl_pt_coords"
                            ] = layout_utils.shift_control_points(
                                data["relative_ctrl_pt_coords"],
                                curr_patt.left,
                                curr_patt.bottom,
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

    def to_dot(self, output_filepath, component_number=None):
        """TODO. Outputs a DOT (and/or XDOT?) representation of the graph.

        Intended for debugging, but we could also use this to bring back a CLI
        option for outputting DOT files.

        Notes
        -----
        Not sure how exactly this should work. Some plans:

        - If component_number is None, then output info for the whole graph; if
          it's not None, output info for just that component (as ordered by
          get_connected_components()).

        - Include all nodes/edges/patterns in the layout? (I guess we could
          uhhh just overlay the nodes onto the patterns? Or we could label the
          patterns as "clusters" in the graph? Or just draw the top-level
          decomposed graph. IDK.)

        - Do we want to include coordinate info from layout()? We can do that
          (with XDOT files), but we can always instead output the graph in
          DOT format.
        """
        raise NotImplementedError

    def to_cytoscape_compatible_format(self):
        """TODO."""
        raise NotImplementedError

    def to_dict(self):
        """Returns a dict representation of the graph usable as JSON.

        (The dict will need to be pushed through json.dumps() first in order
        to make it valid JSON, of course -- e.g. converting Nones to nulls,
        etc.)

        This should be analogous to the SQLite3 database schema previously
        used for MgSc.

        Inspired by to_dict() in Empress.
        """
        # Determine what data we'll export. Each node and edge should have a
        # set of "core attributes," defined in the three lists below, which
        # we'll need to draw the graph.
        #
        # We'll also later go through and figure out what if any extra data
        # (e.g. coverage, GC content, multiplicity) nodes/edges have, and
        # add on additional fields accordingly.
        #
        # These are keyed by integer ID (i.e. what was produced by
        # self.reindex_graph()) <-- TODO, key by nodeid2obj keys instead
        node_fields = [
            "name",
            "length",
            "x",
            "y",
            "width",
            "height",
            "orientation",
            "parent_id",
            "is_dup",
        ]
        # These are keyed by source ID and sink ID (both reindex_graph()
        # integer IDs) <-- TODO, key by edgeid2obj keys instead
        edge_fields = [
            "ctrl_pt_coords",
            "is_outlier",
            "relative_weight",
            "is_dup",
            "parent_id",
        ]
        # One pattern per list in a 2D list
        patt_fields = [
            "pattern_id",
            "left",
            "bottom",
            "right",
            "top",
            "width",
            "height",
            "pattern_type",
            "parent_id",
        ]
        # These dicts map field names to 0-indexed position in a data list
        NODE_ATTRS = {}
        EDGE_ATTRS = {}
        PATT_ATTRS = {}
        # Remove stuff we're going to export from the extra attrs
        # (for non-"internal" but still-essential stuff like orientation)
        # TODO: do this in a more clear way
        self.extra_node_attrs -= set(node_fields)
        self.extra_edge_attrs -= set(edge_fields)
        for fields, attrs in (
            (node_fields + list(self.extra_node_attrs), NODE_ATTRS),
            (edge_fields + list(self.extra_edge_attrs), EDGE_ATTRS),
            (patt_fields, PATT_ATTRS),
        ):
            for i, f in enumerate(fields):
                attrs[f] = i

        def get_node_data(graph_node_data):
            """Utility function for extracting data from a node.

            graph_node_data should be a dictionary-like object, i.e. the node
            data accessible using NetworkX.
            """
            out_node_data = [None] * len(NODE_ATTRS)
            for attr in NODE_ATTRS.keys():
                if attr not in graph_node_data:

                    if attr == "is_dup":
                        # If this node doesn't have "is_dup", then it isn't a
                        # duplicate. No biggie.
                        out_node_data[NODE_ATTRS["is_dup"]] = False

                    elif attr in self.extra_node_attrs:
                        # Extra attrs are optional, so just leave as None
                        continue

                    else:
                        # If we've made it here, then this node really should
                        # have this data -- in which case yeah we should throw
                        # an error.
                        raise ValueError(
                            "Node {} doesn't have attribute {}".format(
                                graph_node_data["name"], attr
                            )
                        )

                else:
                    out_node_data[NODE_ATTRS[attr]] = graph_node_data[attr]

            return out_node_data

        def get_edge_data(srcid, snkid, graph_edge_data):
            """Analogue of get_node_data() for edges."""
            out_edge_data = [None] * len(EDGE_ATTRS)
            is_dup = "is_dup" in graph_edge_data and graph_edge_data["is_dup"]
            for attr in EDGE_ATTRS.keys():
                val = None

                if attr not in graph_edge_data:
                    # If this is a duplicate edge (i.e. connecting a dup node
                    # and its original node), then it isn't a "real" edge -- so
                    # it is to be expected that it won't have this data.
                    #
                    # Even if this is a real edge, if this is an extra attr
                    # (e.g. multiplicity), then this attr is optional and it
                    # not being in this edge is ok.
                    #
                    # In either of the above cases, let's leave this attr as
                    # None; however, if one of the above cases isn't met, then
                    # throw an error because this edge should have this data.
                    if is_dup or attr in self.extra_edge_attrs:
                        continue
                    else:
                        raise ValueError(
                            "Edge {} -> {} doesn't have attribute {}".format(
                                srcid, snkid, attr
                            )
                        )
                else:
                    val = graph_edge_data[attr]
                    out_edge_data[EDGE_ATTRS[attr]] = val

            return (
                graph_edge_data["orig_src"],
                graph_edge_data["orig_tgt"],
                out_edge_data,
            )

        def add_edge(component_dict, edge, edge_data):
            if edge[0] in component_dict["edges"]:
                if edge[1] in component_dict["edges"][edge[0]]:
                    raise ValueError(
                        "Edge {} -> {} added to JSON twice?".format(
                            edge[0], edge[1]
                        )
                    )
                component_dict["edges"][edge[0]][edge[1]] = edge_data
            else:
                component_dict["edges"][edge[0]] = {edge[1]: edge_data}

        # This is the dict we'll return from this function.
        out = {
            "node_attrs": NODE_ATTRS,
            "edge_attrs": EDGE_ATTRS,
            "patt_attrs": PATT_ATTRS,
            "extra_node_attrs": list(self.extra_node_attrs),
            "extra_edge_attrs": list(self.extra_edge_attrs),
            "components": [],
            "input_file_basename": self.basename,
            "input_file_type": self.filetype,
            "total_num_nodes": self.graph.number_of_nodes(),
            "total_num_edges": self.graph.number_of_edges(),
        }

        # Hack: indicate the number of skipped components in the exported data.
        # There are obviously much more efficient ways to do this (e.g. just
        # pass the number of skipped components as a global data property), but
        # this works with the JS I have set up right now and dude it's 5am give
        # me a break
        for n in range(self.num_too_large_components):
            out["components"].append({"skipped": True})

        # For each component:
        # (This is the same general strategy for iterating through the graph as
        # self.layout() uses.)
        for cc_i, cc_tuple in enumerate(
            self.get_connected_components(), self.num_too_large_components + 1
        ):
            this_component = {
                "nodes": {},
                "edges": {},
                "patts": [],
                "bb": self.cc_num_to_bb[cc_i],
                "skipped": False,
            }
            # Go through top-level nodes and collapsed patterns
            for node_id in cc_tuple[0]:
                if self.is_pattern(node_id):
                    # Add pattern data, and data for child + descendant
                    # nodes and edges
                    patt = self.pattid2obj[node_id]
                    patt_queue = deque([patt])
                    while len(patt_queue) > 0:
                        curr_patt = patt_queue.popleft()

                        # Add data for this pattern. All of the stuff in
                        # PATT_ATTRS should be literal attributes of Pattern
                        # objects, so this step is blessedly simple (ish).
                        #
                        # One important thing to note: we store patterns in a
                        # list, not in a dict. This is because we unfortunately
                        # have to care about the order in which patterns are
                        # drawn in the visualization: if we try to draw a
                        # pattern which in turn is a child of another pattern
                        # that hasn't been drawn yet, then Cytoscape.js will
                        # just silently fail. By populating the "patts" list
                        # for each component such that every pattern is added
                        # before its child pattern(s) are, we avoid this
                        # problem.
                        data = [None] * len(PATT_ATTRS)
                        for attr in PATT_ATTRS.keys():
                            data[PATT_ATTRS[attr]] = getattr(curr_patt, attr)
                        this_component["patts"].append(data)

                        # Add data for the nodes within this pattern, and add
                        # patterns within this pattern to the queue.
                        for child_node_id in curr_patt.node_ids:
                            if self.is_pattern(child_node_id):
                                patt_queue.append(
                                    self.pattid2obj[child_node_id]
                                )
                            else:
                                # This is a normal node in a pattern. Add data.
                                data = get_node_data(
                                    self.graph.nodes[child_node_id]
                                )
                                this_component["nodes"][child_node_id] = data

                        # Add data for the edges within this pattern.
                        for edge in curr_patt.subgraph.edges:
                            os, ot, data = get_edge_data(
                                edge[0],
                                edge[1],
                                curr_patt.subgraph.edges[edge],
                            )
                            add_edge(this_component, [os, ot], data)
                else:
                    # Add node data (top level, i.e. not present in any
                    # patterns)
                    if node_id in this_component["nodes"]:
                        raise ValueError(
                            "Node {} added to JSON twice?".format(node_id)
                        )
                    data = get_node_data(self.graph.nodes[node_id])
                    this_component["nodes"][node_id] = data

            # Go through top-level edges and add data
            for edge in self.decomposed_graph.subgraph(cc_tuple[0]).edges:
                os, ot, data = get_edge_data(
                    edge[0],
                    edge[1],
                    self.decomposed_graph.edges[edge],
                )
                add_edge(this_component, [os, ot], data)

            # Since we're going through components in the order dictated by
            # self.get_connected_components() we can just add component JSONs
            # to out["components"] as we go through things.
            out["components"].append(this_component)
        return out

    def to_json(self):
        """Calls self.to_dict() and then pushes that through json.dumps().

        Why are these even separate functions in the first place? Probably
        testing, mostly -- it's easier to test that a dict contains a certain
        element, etc. than it would be if we had to go through the dict -> JSON
        str -> dict song and dance for every test.
        """
        return json.dumps(self.to_dict())

    def rotate_from_TB_to_LR(self):
        """Rotates the graph so it flows from L -> R rather than T -> B."""
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
            if "x" not in data:
                print(data, "tf lol")
            data["x"], data["y"] = layout_utils.rotate(data["x"], data["y"])

        # Rotate edges
        for edge in self.decomposed_graph.edges:
            data = self.decomposed_graph.edges[edge]
            data["ctrl_pt_coords"] = layout_utils.rotate_ctrl_pt_coords(
                data["ctrl_pt_coords"]
            )
