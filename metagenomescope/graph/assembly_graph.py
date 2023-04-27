import math
import json
import os
import subprocess
from copy import deepcopy
from operator import itemgetter
from collections import deque
import numpy
import networkx as nx
import pygraphviz


from .. import parsers, config, layout_utils
from ..msg_utils import operation_msg, conclude_msg
from ..errors import GraphParsingError, GraphError, WeirdError
from . import validators
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
    is done, thus represents the "fully uncollapsed" graph.

    The .decomposed_graph object describes the "top-level" assembly graph
    structure. As we identify patterns in the graph, we will remove these nodes
    and edges from the .decomposed_graph object, replacing them with their
    parent pattern node. After decomposition is done, this object thus
    represents the "fully collapsed" graph. (Or, phrased differently: if you
    recursively replace all pattern nodes in the decomposed graph with their
    child nodes and edges, then the resulting graph should be equivalent to
    the uncollapsed graph stored in .graph.)

    References
    ----------
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

        After you create a graph, you should usually call the layout() method
        to assign coordinates to nodes and edges in the graph.

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
        operation_msg(f"Loading the assembly graph, {self.basename}...")
        # NOTE: Ideally we'd just return this along with the graph from
        # parsers.parse(), but uhhhh that will make me refactor
        # like 20 tests and I don't want to do that ._.
        self.filetype = parsers.sniff_filetype(self.filename)
        self.graph = parsers.parse(self.filename)
        conclude_msg()

        operation_msg(
            (
                f"Graph contains {len(self.graph.nodes):,} node(s) and "
                f"{len(self.graph.edges):,} edge(s)."
            ),
            newline=True,
        )

        # Remove nodes/edges in components that are too large to lay out.
        operation_msg(
            f"Removing components with > {self.max_node_count:,} nodes and/or "
            f"> {self.max_edge_count:,} edges..."
        )
        self.num_too_large_components = 0
        self._remove_too_large_components()
        conclude_msg()
        operation_msg(
            f"Removed {self.num_too_large_components:,} such component(s).",
            newline=True,
        )

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
        # objects' unique IDs.
        operation_msg("Initializing node and edge graph objects...")
        self._init_graph_objs()
        conclude_msg()

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
        self.ptype2collection = {
            config.PT_BUBBLE: self.bubbles,
            config.PT_CHAIN: self.chains,
            config.PT_CYCLICCHAIN: self.cyclic_chains,
            config.PT_FRAYEDROPE: self.frayed_ropes,
        }

        # Holds the top-level decomposed graph.
        # PERF / NOTE: Ideally we'd avoid creating this completely if
        # --patterns is False (this way we avoid the extra memory usage).
        operation_msg("Creating a copy of the graph for decomposition...")
        self.decomposed_graph = deepcopy(self.graph)
        conclude_msg()

        # Node/edge scaling is done *before* pattern detection, so duplicate
        # nodes/edges created during pattern detection shouldn't influence
        # relative scaling stuff.
        operation_msg("Scaling nodes based on lengths...")
        self._scale_nodes()
        conclude_msg()

        self._scale_edges()

        # TODO: During the April 2023 refactor, WE ARE HERE. Need to update
        # these functions to set these internal attributes (width, height,
        # relative_length, ...) as attributes of Node/Edge attributes --
        # blessedly, leaving user-provide Node/Edge data separate.
        if self.find_patterns:
            operation_msg("Decomposing the graph into patterns...")
            self._hierarchically_identify_patterns()
            conclude_msg()
            operation_msg(
                f"Found {len(self.bubbles):,} bubble(s), "
                f"{len(self.chains):,} chain(s), "
                f"{len(self.cyclic_chains):,} cyclic chain(s), and "
                f"{len(self.frayed_ropes):,} frayed rope(s)."
            )

        # Defer this until after we do pattern decomposition, to account for
        # split nodes. (At this point we have already called _scale_nodes() --
        # so the presence of split nodes shouldn't change how other nodes in
        # the graph are scaled.)
        # TODO -- update _compute_node_dimensions() to run on the decomposed
        # graph, not the original graph
        self._compute_node_dimensions()

        # Since layout can take a while, we leave it to the creator of this
        # object to call .layout() (if for example they don't actually need to
        # layout the graph, and they just want to do pattern detection).
        #
        # Some functions require that layout has already been performed,
        # though. These functions can just use this flag to figure out if they
        # should immediately fail with an error.
        self.layout_done = False

    def _init_graph_objs(self):
        """Initializes Node and Edge objects for the original graph.

        Also, clears the NetworkX data stored for each node and edge in the
        graph (don't worry, this data isn't lost -- it's saved in the
        corresponding Node and Edge objects' .data attributes).

        Finally, this relabels nodes in the graph to match their corresponding
        Node object's unique_id; and adds an "uid" attribute to edges' NetworkX
        data that matches their corresponding Edge object's unique_id.

        Notes
        -----
        We may add more Node and Edge objects as we perform pattern detection
        and node splitting. That will be done separately; this method just
        establishes a "baseline."
        """
        oldid2uniqueid = {}
        for node_name in self.graph.nodes:
            node_id = self._get_unique_id()
            data = deepcopy(self.graph.nodes[node_name])
            self.nodeid2obj[node_id] = Node(node_id, node_name, data)
            self.extra_node_attrs |= set(data.keys())
            # Remove node data from the graph (we've already saved it in the
            # Node object's .data attribute).
            self.graph.nodes[node_name].clear()
            # We'll re-label nodes in the graph, to make it easy to associate
            # them with their corresponding Node objects. (Don't worry -- we
            # already passed node_name to the corresponding Node object for
            # this node, so the user will still see it in the visualization.)
            oldid2uniqueid[node_name] = node_id

        nx.relabel_nodes(self.graph, oldid2uniqueid, copy=False)

        for e in self.graph.edges(data=True, keys=True):
            edge_id = self._get_unique_id()
            # e is a 4-tuple of (source ID, sink ID, key, data dict)
            self.edgeid2obj[edge_id] = Edge(
                edge_id, e[0], e[1], deepcopy(e[3])
            )
            self.extra_edge_attrs |= set(e[3].keys())
            # Remove edge data from the graph.
            self.graph.edges[e[0], e[1], e[2]].clear()
            # Edges in NetworkX don't really have "IDs," but we can use the
            # (now-cleared) data dict in the graph to store their ID. This will
            # make it easy to associate this edge with its Edge object.
            self.graph.edges[e[0], e[1], e[2]]["uid"] = edge_id

    def _remove_too_large_components(self):
        """Removes too-large components from the graph early on.

        Notes
        -----
        Maybe we should save information about *which* nodes and edges exist in
        these components, so that -- if users search for these nodes / edges --
        we could inform the user "hey, this object is in a component that
        didn't get laid out." Buuuuut that's a problem for another day.
        """
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

    def _get_unique_id(self):
        """Returns an int guaranteed to be usable as a unique new ID.

        We assign these unique IDs to nodes, edges, and patterns. We could
        probably get away with letting there be some overlap between node and
        edge IDs, but I don't want to even think about that stuff. So we ensure
        that ANY two nodes, edges, or patterns (or one node and one edge, etc.)
        have different unique IDs.
        """
        # this is what they pay me the big bucks for, folks. this is home-grown
        # organic computer science right here
        new_id = self.num_objs
        self.num_objs += 1
        return new_id

    def _make_new_split_node(self, original_node_id, split):
        """Creates a new "split" node based on another node.

        Parameters
        ----------
        original_node_id: int
            ID of the original node from which we'll create this split node.
            This should correspond to an entry in self.nodeid2obj.

        split: str
            Should be either config.SPLIT_LEFT or config.SPLIT_RIGHT.

        Returns
        -------
        new_node_id: int
            The ID of the split node we created.
        """
        if split != config.SPLIT_LEFT and split != config.SPLIT_RIGHT:
            raise WeirdError(f"Unrecognized split value: {split}")
        new_node_id = self._get_unique_id()
        other_node = self.nodeid2obj[original_node_id]
        # NOTE: Deep copying the data here is probably unnecessary,
        # since I don't think we'll ever *want* it to be different
        # between a node and its split copy. But whatever.
        new_node = Node(
            new_node_id,
            other_node.name,
            deepcopy(other_node.data),
            split=split,
        )
        new_node.set_scale_vals_from_other_node(other_node)
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
            the is_valid attribute of this is True. This may or may not have
            start/end nodes defined.

        Returns
        -------
        (Pattern, int or None, int or None): (pattern, left ID, right ID)
        """
        pattern_id = self._get_unique_id()
        self.decomposed_graph.add_node(pattern_id)
        patt_nodes = set(validation_results.nodes)

        # We may need to create new Nodes (one if we split the start node of
        # the pattern, and one if we split the end node of the pattern --
        # assuming that the pattern has individual start/end nodes). We'll
        # store these new Nodes' IDs in these variables, and return them.
        left_node_id = None
        right_node_id = None

        if validation_results.has_start_end:

            # Do we need to split the start node of this pattern?
            start_id = validation_results.start_node
            start_pred = self.decomposed_graph.pred[start_id]
            start_incoming_nodes_outside_pattern = set(start_pred) - patt_nodes

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
                self.nodeid2obj[start_id].make_into_right_split()
                # Route edges from start_incoming_nodes_outside_pattern to
                # the left node
                for incoming_node_id in start_incoming_nodes_outside_pattern:
                    # We convert the start_pred object to a list, because when
                    # we re-route edges here then it adjusts the dictionary
                    for edge_key in list(start_pred[incoming_node_id]):
                        e_uid = self.graph.edges[
                            incoming_node_id, start_id, edge_key
                        ]["uid"]
                        self.edgeid2obj[e_uid].reroute_tgt(left_node_id)
                        self.edgeid2obj[e_uid].reroute_dec_tgt(pattern_id)
                        # We keep the edge ID the same, so ... even though we
                        # reroute it in the graphs, this is still the same edge.
                        for g in (self.graph, self.decomposed_graph):
                            g.add_edge(
                                incoming_node_id, left_node_id, uid=e_uid
                            )
                            g.remove_edge(incoming_node_id, start_id, edge_key)

                # All other edges (mostly outgoing edges, but maybe incoming
                # edges from within the pattern) will be routed by default to
                # the right node. Because... the right node is just the
                # original node, but renamed! Cool.

                # Add a fake edge between the left and right node
                fake_edge_id = self._get_unique_id()
                fake_edge = Edge(
                    fake_edge_id, left_node_id, start_id, {}, is_fake=True
                )
                self.edgeid2obj[fake_edge_id] = fake_edge
                self.graph.add_edge(left_node_id, start_id, uid=fake_edge_id)
                self.decomposed_graph.add_edge(
                    left_node_id, pattern_id, uid=fake_edge_id
                )

            # Do we need to split the end node of this pattern?
            end_id = validation_results.end_node
            end_adj = self.decomposed_graph.adj[end_id]
            end_outgoing_nodes_outside_pattern = set(end_adj) - patt_nodes

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
                self.nodeid2obj[end_id].make_into_left_split()
                # Route edges from the right node to
                # end_outgoing_nodes_outside_pattern
                for outgoing_node_id in end_outgoing_nodes_outside_pattern:
                    for edge_key in list(end_adj[outgoing_node_id]):
                        e_uid = self.graph.edges[
                            end_id, outgoing_node_id, edge_key
                        ]["uid"]
                        self.edgeid2obj[e_uid].reroute_src(right_node_id)
                        self.edgeid2obj[e_uid].reroute_dec_src(pattern_id)
                        for g in (self.graph, self.decomposed_graph):
                            g.add_edge(
                                right_node_id, outgoing_node_id, uid=e_uid
                            )
                            g.remove_edge(end_id, outgoing_node_id, edge_key)

                # Add a fake edge between the left and right node
                fake_edge_id = self._get_unique_id()
                fake_edge = Edge(
                    fake_edge_id, end_id, right_node_id, {}, is_fake=True
                )
                self.edgeid2obj[fake_edge_id] = fake_edge
                self.graph.add_edge(end_id, right_node_id, uid=fake_edge_id)
                self.decomposed_graph.add_edge(
                    pattern_id, right_node_id, uid=fake_edge_id
                )

        # For every incoming edge from outside this pattern to a node within
        # this pattern: route this edge to just point (in the decomposed graph)
        # to the new pattern node. This should only actually change the graph
        # if (1) we didn't do splitting, or (2) the pattern has weird incoming
        # edges from outside nodes into its middle nodes or something (this
        # shouldn't happen in practice, but maybe when we add back support for
        # arbitrary user-defined patterns it could happen).
        in_edges = self.decomposed_graph.in_edges(patt_nodes, keys=True)
        p_in_edges = list(filter(lambda e: e[0] not in patt_nodes, in_edges))
        for e in p_in_edges:
            e_uid = self.decomposed_graph.edges[e]["uid"]
            self.edgeid2obj[e_uid].reroute_dec_tgt(pattern_id)
            # We will remove the edge that this is replacing (e) soon, when we
            # call self.decomposed_graph.remove_nodes_from(patt_nodes).
            self.decomposed_graph.add_edge(e[0], pattern_id, uid=e_uid)

        # For every outgoing edge from inside this pattern to a node outside
        # this pattern: route this edge to originate from (in the decomposed
        # graph) the new pattern node. Like above.
        out_edges = self.decomposed_graph.out_edges(patt_nodes, keys=True)
        p_out_edges = list(filter(lambda e: e[1] not in patt_nodes, out_edges))
        for e in p_out_edges:
            e_uid = self.decomposed_graph.edges[e]["uid"]
            self.edgeid2obj[e_uid].reroute_dec_src(pattern_id)
            # again, don't worry, we'll remove the edge this is replacing soon
            self.decomposed_graph.add_edge(pattern_id, e[1], uid=e_uid)

        subgraph = self.decomposed_graph.subgraph(patt_nodes).copy()
        child_edges = [
            self.edgeid2obj[uid] for _, _, uid in subgraph.edges(data="uid")
        ]

        # Remove the children of this pattern (and any edges incident on them,
        # which should be limited -- after the splitting and rerouting steps
        # above -- to edges in child_edges) from the decomposed DiGraph.
        self.decomposed_graph.remove_nodes_from(patt_nodes)

        p = Pattern(
            pattern_id,
            validation_results.pattern_type,
            validation_results,
            child_edges,
            self,
        )
        self.pattid2obj[pattern_id] = p
        self.ptype2collection[validation_results.pattern_type].append(p)
        return p, left_node_id, right_node_id

    def _hierarchically_identify_patterns(self):
        """Run all of our pattern detection algorithms on the graph repeatedly.

        This is the main Fancy Thing we do, besides layout.

        TODOs: behavior
        ---------------
        2. Disallow the presence of frayed ropes within frayed ropes, even in
           the middle. (Again, I think the way to do this is to wrap the
           validator in another function that figures out if any of the nodes
           in a tentative FR are also FRs, and fails if so.)
        3. If we find a chain located in another chain (or located within a
           cyclic chain), merge it into its parent.
            - How do we do this? I guess we'd move all of the nodes and edges
              in the smaller chain into the parent chain, and update
              pattid2obj. Not sure if anything else.
        4. Allow frayed ropes to contain an uncollapsed trivial chain in their
           middle nodes. (Doable by just modifying the frayed rope code to
           allow for any sort of chains -- doesn't have to be specific. Unlike
           the bubble code, we don't need to worry about first detecting the
           real chains in the frayed rope, because by the time we identify
           frayed ropes we've already identified all real chains in the graph.
           (And we can't have frayed ropes within chains.)
        5. After we find frayed ropes, identify cases where splitting wasn't
           necessary (where there exist "trivial" chains from a left node -->
           the pattern it was created for, or the pattern --> its right node)
           and merge the split node(s) back in with the pattern. This will
           require a traversal of all nodes in the graph, I think (not just the
           top level of the decomposed graph), since trivial chains can be
           located in bubbles / frayed ropes.

        TODOs: code
        -----------
        6. See if we can move the splitting code in _add_pattern() to another
           helper function (that takes as input the graph and decomposed
           graph?), or something? if feasible.
        7. Try to remove the subgraph argument from Pattern...? I'd prefer if
           it just keeps a reference to this AssemblyGraph object. It looks
           like Pattern only needs the subgraph in order to figure out what
           edges it contains -- maybe just pass the edge IDs to the pattern,
           then have it refer back to this AssemblyGraph when it needs to
           update them? yeah, that makes sense.
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
                # automatic boundary duplication for all non-frayed rope
                # patterns and (2) the guarantee of minimality (each bulge,
                # chain, bubble, and cyclic chain are guaranteed not to contain
                # any undetected smaller patterns within them).
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
                        pobj, ls, rs = self._add_pattern(validation_results)

                        # Remove child nodes of this pattern from consideration as
                        # future start nodes of other patterns. (Don't worry,
                        # self._add_pattern() already takes care of removing them
                        # from the decomposed graph.)
                        for pn in pobj.node_ids:
                            # We use .discard() rather than .remove() since we
                            # already popped n from candidate_nodes (and .remove()
                            # throws an error if we try to remove an element that
                            # isn't present in the set)
                            candidate_nodes.discard(pn)

                        # We don't need to add the new pattern object itself (or the
                        # left split node, ls) to candidate_nodes, but we add
                        #
                        # (1) the right split node, rs, if present, and
                        # (2) the incoming nodes [located outside of the newly-
                        #     identified pattern] of the left split node, ls, if
                        #     present
                        #
                        # The reason for only adding these nodes: we know that ls
                        # and the new pattern node can't be the start of a chain,
                        # cyclic chain, bulge, bubble, or frayed rope. (My proof of
                        # this: I thought about it for a while and now my head
                        # hurts.) They could be located *within* one of these
                        # structures that starts at another node, though, which is
                        # why we add ls' predecessors.
                        if rs is not None:
                            candidate_nodes.add(rs)
                        if ls is not None:
                            for incoming_node in self.decomposed_graph.pred[
                                ls
                            ]:
                                if incoming_node not in pobj.node_ids:
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

        # Now, identify frayed ropes, which are a "top-level only" pattern.
        # There aren't any other "top-level only" patterns as of writing, but I
        # guess you could add them here if you wanted.
        # TODO -- modify the frayed rope validator to allow uncollapsed trivial
        # chains in the middle
        top_level_candidate_nodes = set(self.decomposed_graph.nodes)
        while len(top_level_candidate_nodes) > 0:
            n = top_level_candidate_nodes.pop()
            validation_results = validators.is_valid_frayed_rope(
                self.decomposed_graph, n
            )
            if validation_results:
                # Mostly the same logic as for when we found a pattern above --
                # but here, we don't bother adding anything to the "candidates"
                # after finding a frayed rope, because we don't perform node
                # splitting on frayed rope boundaries (at least, as of writing)
                # and because frayed ropes can't be contained in other patterns
                pobj, ls, rs = self._add_pattern(validation_results)
                for pn in pobj.node_ids:
                    top_level_candidate_nodes.discard(pn)

        # No need to go through the nodes and edges in the top level of the
        # graph and record that they don't have a parent pattern -- their
        # parent_id attrs default to None

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
                    "Split nodes shouldn't exist in the graph yet."
                )
            if "length" in n.data:
                lengths[ni] = n.data["length"]
        return lengths

    def _scale_nodes_all_uniform(self):
        for node in self.nodeid2obj.values():
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
        for node in self.nodeid2obj.values():
            area = config.MIN_NODE_AREA + (
                node.relative_length * config.NODE_AREA_RANGE
            )
            # Again, in the interface the height will be the width and the
            # width will be the height
            node.height = area**node.longside_proportion
            node.width = area / node.height

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
        if node_id >= self.num_objs or node_id < 0:
            raise WeirdError(f"Node ID {node_id} seems out of range.")
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
        """Lays out the assembly graph."""
        operation_msg("Laying out the graph...", True)
        self._layout()
        operation_msg("...Finished laying out the graph.", True)

        operation_msg("Rotating and scaling things as needed...")
        self._rotate_from_TB_to_LR()
        conclude_msg()

        self.layout_done = True

    def _layout(self):
        """Lays out the graph's components, handling patterns specially."""
        # Do layout one component at a time.
        # (We don't bother checking for skipped components, since we should
        # have already called self._remove_too_large_components().)
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

    def _rotate_from_TB_to_LR(self):
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

    def dump_dots(
        self,
        output_dir,
        graph_fn="graph.gv",
        decomposed_graph_fn="dec-graph.gv",
        make_pngs=True,
    ):
        """Writes out the (un)collapsed and collapsed graphs in DOT format.

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

        make_pngs: bool
            If True, convert all of the DOT files we wrote out to PNGs; if
            False, don't. The PNG files for the uncollapsed and collapsed graph
            will be named "graph.png" and "dec-graph.png", respectively.

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

    def _fail_if_layout_not_done(self, fn_name):
        if not self.layout_done:
            raise GraphError(
                "You need to call .layout() on this AssemblyGraph object "
                f"before calling .{fn_name}()."
            )

    def to_dict(self):
        """Returns a dict representation of the graph usable as JSON.

        (The dict will need to be pushed through json.dumps() first in order
        to make it valid JSON, of course -- e.g. converting Nones to nulls,
        etc.)

        This should be analogous to the SQLite3 database schema previously
        used for MgSc.

        Inspired by to_dict() in Empress.
        """
        self._fail_if_layout_not_done("to_dict")
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
        # self._layout() uses.)
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
        self._fail_if_layout_not_done("to_json")
        return json.dumps(self.to_dict())
