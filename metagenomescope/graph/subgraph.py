# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.

import logging
import itertools
import networkx as nx
from .. import config, ui_config, ui_utils, name_utils
from ..layout import Layout
from ..errors import WeirdError
from . import graph_utils
from .pattern_stats import PatternStats
from .draw_results import DrawResults
from .invalidated_edge import InvalidatedEdge


class Subgraph(object):
    """Represents an arbitrary subgraph in an assembly graph.

    There is no requirement that this subgraph forms a connected component
    or anything.

    Notes
    -----
    We assume that the contents of this Subgraph won't change after
    initialization; probably don't call _add_node(), _add_edge(), or
    _add_pattern() from outside of this object unless you're doing something
    fancy.
    """

    def __init__(
        self,
        unique_id,
        name,
        nodes,
        edges,
        patterns,
        node_centric=True,
        length_field="length",
        record_node_names=True,
        count_positive_names=True,
    ):
        """Initializes this Subgraph object.

        Parameters
        ----------
        unique_id: int

        name: str

        nodes: list of Node

        edges: list of Edge

        patterns: list of Pattern

        node_centric: bool
            True means that nodes have sequences (and, more importantly for
            this object, lengths). False means that edges have sequences.

        length_field: str
            Used to access lengths for nodes or edges.

        record_node_names: bool
            True means that we should look at node names when figuring out
            e.g. the lexicographically smallest name in this Subgraph. False
            means we should look at edge IDs.

            This should be True for all types of graphs except Flye DOT files
            -- because LJA DOT files are not guaranteed to have meaningful edge
            IDs, we can't just get this information from node_centric.

        count_positive_names: bool
            True means we should do the work of counting all positive node or
            edge names (the question of nodes vs. edges is determined by
            record_node_names); False means we should just skip that. This
            option is here because some graphs (e.g. MetaCarvel GML files) have
            nodes without orientations in their name, so there would be no
            point counting this anyway.

        Notes
        -----
        It is the caller's responsibility to only include a pattern if all
        of the children of the pattern are present in this subgraph. We don't
        recursively go through the patterns' descendants here to check stuff.
        """
        self.unique_id = unique_id
        self.name = name
        self.nodes = []
        self.edges = []
        self.patterns = []

        # We will compute the total length of the nodes or edges in this
        # Subgraph, to help with sorting Subgraphs.
        self.node_centric = node_centric
        self.length_field = length_field
        self.total_length = 0

        self.record_node_names = record_node_names
        # Record the lexicographically smallest node or edge name (determined
        # by self.record_node_names), to use as a tiebreaker when sorting
        # subgraphs. The orientationless version is used to ensure that a
        # component and its twin (if present) go next to each other, and
        # the normal version (with an orientation, assuming that orientations
        # are given in names in this graph) is used as a final tiebreaker to
        # ward of the dreadful case where two twin components are perfectly
        # identical (down to even their numbers of positive names...).
        self.min_name_orientationless = None
        self.min_name = None
        self.count_positive_names = count_positive_names
        # If self.count_positive_names is True, then record the number of
        # positive node or edge names we see. (If it's False, then just leave
        # this at 0 forever.)
        self.num_positive_names = 0

        # Keep track of node basenames we have seen already, so we don't
        # double-count X-L and X-R as two nodes
        self.seen_basenames = set()

        # Number of nodes in this Subgraph that are not split.
        self.num_unsplit_nodes = 0

        # Number of split nodes in this Subgraph (including both left and
        # right splits: e.g. if a subgraph contains exactly one instance of a
        # node being split from 4-L ==> 4-R, then num_split_nodes should be 2).
        self.num_split_nodes = 0

        # Number of total nodes in this Subgraph (should be equal to
        # num_unsplit_nodes + num_split_nodes).
        self.num_total_nodes = 0

        # Total number of "full" nodes (treating the left and right part of a
        # split node as one "full" node). Should be equal to
        # num_unsplit_nodes + (num_split_nodes / 2).
        self.num_full_nodes = 0

        # Number of edges in this Subgraph, not including fake edges from a
        # left split node to a right split node.
        self.num_real_edges = 0

        # Number of fake edges in this Subgraph.
        self.num_fake_edges = 0

        # Total number of edges in this Subgraph (should be equal to
        # num_real_edges + num_fake_edges).
        self.num_total_edges = 0

        # PatternStats for this Subgraph.
        self.pattern_stats = PatternStats()

        # map node IDs to objects; useful for decoupling, etc
        self.nodeid2obj = {}

        # map pattern IDs to objects. Useful if we want to e.g. figure out
        # what type of pattern an edge has (relevant to
        # layout_utils.flatten_some_edges()).
        self.pattid2obj = {}

        # Whether or not this subgraph was decoupled, and if so subsets of
        # things to draw for the decoupled version of this subgraph. Only
        # relevant if this subgraph is "strand-tangled."
        self.decoupling_done = False
        self.dc_shown_node_ids = set()
        self.dc_shown_patt_ids = set()
        # This does not include the IDs of invalidated edges.
        self.dc_shown_edge_ids = set()
        # This does! Well, really, this includes the full InvalidatedEdge
        # objects, since we've gotta store them somewhere...
        self.dc_inval_edges = []

        for n in nodes:
            self._add_node(n)
        for e in edges:
            self._add_edge(e)
        for p in patterns:
            self._add_pattern(p)
        self.round_num_full_nodes()

        # no need to hold onto THAT
        del self.seen_basenames

    def _get_repr_counts(self):
        return (
            f"{ui_utils.pluralize(self.num_total_nodes, 'node')}; "
            f"{ui_utils.pluralize(self.num_total_edges, 'edge')}; "
            f"{ui_utils.pluralize(self.pattern_stats.sum(), 'pattern')}"
        )

    def __repr__(self):
        return (
            f"{self.name} ({self._get_repr_counts()}; "
            f"length {self.total_length:,})"
        )

    def _add_length(self, obj):
        if self.length_field not in obj.data:
            raise WeirdError(f'{obj} has no field "{self.length_field}"?')
        self.total_length += obj.data[self.length_field]

    def _record_name(self, name):
        # Try to update the lexicographically minimum name
        on = name_utils.get_orientationless_name(name)
        if (
            self.min_name_orientationless is None
            or on < self.min_name_orientationless
        ):
            self.min_name_orientationless = on
            self.min_name = name
        if self.count_positive_names and not name_utils.is_rev(name):
            self.num_positive_names += 1

    def _add_node(self, node):
        self.nodes.append(node)
        self.nodeid2obj[node.unique_id] = node
        # If we are counting node lengths (because this is a node-centric
        # graph), then record length only once for each node basename (so
        # X-L and X-R only contribute to the total length once).
        #
        # Similarly, if we are recording node names, then only count those
        # once per basename (aka once per full node)
        bn = node.basename
        if bn not in self.seen_basenames:
            if self.node_centric:
                self._add_length(node)
            if self.record_node_names:
                self._record_name(node.basename)
            self.seen_basenames.add(bn)

        # It is possible for only one of a split node to be in a Subgraph
        # (if we are drawing around nodes). This is why we don't lump this
        # stuff in with the seen_basenames block of code above.
        if node.is_split():
            self.num_split_nodes += 1
            self.num_full_nodes += 0.5
        else:
            self.num_unsplit_nodes += 1
            self.num_full_nodes += 1
        self.num_total_nodes += 1

    def round_num_full_nodes(self):
        # leave node counts like 23.5 as 23.5, but turn node counts
        # like 23.0 back into just 23 (since we know that num_full_nodes
        # must end with .0 or .5)
        self.num_full_nodes = ui_utils.round_to_int_if_close(
            self.num_full_nodes
        )

    def _add_edge(self, edge):
        self.edges.append(edge)
        if edge.is_fake:
            self.num_fake_edges += 1
        else:
            self.num_real_edges += 1
            if not self.node_centric:
                self._add_length(edge)
            if not self.record_node_names:
                self._record_name(edge.get_userspecified_id())
        self.num_total_edges += 1

    def _add_pattern(self, pattern):
        self.patterns.append(pattern)
        self.pattern_stats.update(pattern.pattern_type)
        self.pattid2obj[pattern.unique_id] = pattern

    def get_objs(self):
        return itertools.chain(self.nodes, self.edges, self.patterns)

    def decouple(self, g, nodename2objs):
        """Tries to decouple this subgraph.

        Parameters
        ----------
        g: nx.MultiDiGraph
            NetworkX representation of the full assembly graph of which this
            subgraph is, um, a subgraph. This should correspond to an
            AssemblyGraph.graph object.

        nodename2objs: dict of str -> list of Node

        Returns
        -------
        bool
            True if this subgraph was strand-tangled (i.e. decoupling changed
            it), False if not.

        Notes
        -----
        - There is some ambiguity in how we determine which node orientations
          to fix. Like, as long as we consider all nodes in this subgraph, any
          traversal approach "works" (i.e. we will end up showing all nodes
          once with a given orientation). Our goal is more specifically to
          minimize the amount of invalidated edges while maximizing the
          "linearity" of the resulting layout.

          We currently just use NetworkX's bfs_layers() function, which seems
          to work well for this, but maybe there are other methods that would
          be better (that explicitly "weight" outgoing edges more, in order to
          increase linearity).

          Consider a subgraph like X -> Y -> ... -> -Y -> -X
                                   A -> B -> ... -> -B -> -A, where the ...s
          indicate these four paths kind of mixing together due to inverted
          repeats or something.

          In this graph, we want to ideally end up with XY...(-B)(-A) or
          AB...(-Y)(-X). Nothing is *wrong* if we end up with XY...BA or
          AB...YX or something -- since those are still valid decoupled
          representations of this subgraph -- but they are not ideal, because
          they are not the most linear way of representing it. Probably there
          is a good way to formalize this that I am just missing out on --
          I guess minimizing the number of "back edges" ...?
        """
        if self.decoupling_done:
            raise WeirdError(f"{self} is already decoupled")
        if len(self.nodes) <= 1:
            return False

        # maps orientationless node names (i.e. "X" for both X and -X) to a
        # fixed orientation
        on2orient = {}

        # Fix the highest-degree + node in this subgraph as "shown"
        #
        # In a perfectly symmetric subgraph, the highest degree node X
        # should also have a twin node -X with the same degree (right?)
        # Thus, we limit the max-degree node search here to + nodes.
        #
        # Also: we use is_fwd() instead of the node "orientation" data because
        # the DOT parsing code doesn't assign orientations even to LJA DOT
        # nodes, at least for now.
        #
        # Also also, we sort the nodes by name first to make this consistent.
        # (Node IDs should be assigned consistently, so sorting using IDs
        # should be kosher, but let's be paranoid.)
        fwd_nodes = [n for n in self.nodes if name_utils.is_fwd(n.basename)]
        sorted_fwd_nodes = graph_utils.get_sorted_nodes(fwd_nodes)
        sorted_fwd_nids = [n.unique_id for n in sorted_fwd_nodes]
        mid = graph_utils.get_max_degree_node(g, sorted_fwd_nids)
        m = self.nodeid2obj[mid]
        on2orient[name_utils.get_orientationless_name(m.basename)] = config.FWD

        # Record max-degree node (and counterpart, if applicable & present in
        # this subgraph) as shown
        shown_nids = set()
        graph_utils.add_node_and_counterpart_ids(
            shown_nids, m, self.nodeid2obj
        )

        # Go through the graph and fix node orientations.
        # We use BFS to do this, which seems to work ok; see docstring.
        # Note that computing the induced subgraph and creating an
        # undirected graph view from it could be slow (but I doubt it
        # will be a bottleneck). If needed we can do BFS/etc manually
        ug = nx.induced_subgraph(g, self.nodeid2obj.keys()).to_undirected(
            as_view=True
        )
        for nids in nx.bfs_layers(ug, mid):
            layer_nodes = [self.nodeid2obj[i] for i in nids]
            # sort the nodes in each layer to make this consistent, so that if
            # X and -X occur in the same layer then the choice of which we pick
            # is consistent
            sorted_layer_nodes = graph_utils.get_sorted_nodes(layer_nodes)
            for n in sorted_layer_nodes:
                on = name_utils.get_orientationless_name(n.basename)
                if on not in on2orient:
                    on2orient[on] = name_utils.get_orientation(n.basename)
                    graph_utils.add_node_and_counterpart_ids(
                        shown_nids, n, self.nodeid2obj
                    )

        # Was this subgraph changed by fixing node orientations?
        # It might not have been, if it was not strand-tangled. (Even for
        # entire components, we could encounter this case in FASTG / LJA DOT
        # files, I guess -- that is, components with no twin that are
        # nonetheless not strand-tangled.)
        if len(shown_nids) == len(self.nodes):
            # no, this subgraph was not changed. move on.
            return False
        elif len(shown_nids) > len(self.nodes):
            # like, i know it should never happen. i just wanna be sure
            raise WeirdError(f"{self} caused the apocalypse what even")

        # Okay, we know this subgraph was changed by fixing node
        # orientations, since |shown nodes| < |nodes|.

        # If this Subgraph is an entire Component, and (s, t) and (-t, -s)
        # correspond to DIFFERENT amounts of (real) edges, then we can still
        # do decoupling... but let's emit a LOUD warning that drawing this
        # Component with decoupling may not show some edges. (This should only
        # happen with "explicit" filetypes that have node orientations -- so,
        # FASTG and LJA DOT, I think. And even then this really shouldn't
        # happen in practice.)
        #
        # In theory this warning could also be applicable to certain Subgraphs
        # that actually include s, t, -s, and -t, but adapting that may be
        # kind of messy.
        if hasattr(self, "cc_num"):
            graph_utils.warn_if_cc_edge_cts_asymmetric(self)

        # Record what edges will be drawn in the decoupled version of this
        # subgraph...
        shown_eids = set()
        # ...as well as InvalidatedEdge objects created to represent edges that
        # cannot be shown as-is.
        inval_edgetups = set()
        inval_edges = []
        for e in self.edges:
            src_shown = e.new_src_id in shown_nids
            tgt_shown = e.new_tgt_id in shown_nids
            inval_type = None
            if src_shown:
                if tgt_shown:
                    # If BOTH {src, tgt} are shown, then we can draw this edge!
                    shown_eids.add(e.unique_id)
                else:
                    inval_type = config.INVAL_TGT
            else:
                if tgt_shown:
                    inval_type = config.INVAL_SRC
                # If NEITHER {src, tgt} is shown, then we'll draw the RC of
                # this edge (assuming that this subgraph is symmetric, which
                # is checked by that warning above).

            if inval_type is not None:
                # Exactly one of {src, tgt} is shown. This edge is invalidated.
                #
                # Consider the case where there are parallel invalidated edges
                # (multiple from s -> t and multiple from -t -> -s). We could
                # show (with the funky port stuff) either all edges from
                # s -> t, or all edges from -t -> -s, but it would be confusing
                # to show a mix of edges. Thus, we arbitrarily say that we will
                # only show invalidated edges from one of the two (whichever we
                # see first and record in inval_edgetups).
                #
                # Note that we use basenames here. Let's say node "1" is split
                # into "1-L --> 1-R", but node "-1" is not split. Using
                # basenames makes it clear that e.g. 1-R --> 2 is symmetric to
                # -2 --> -1, since it becomes (1, 2) vs. (-2, -1).
                s = self.nodeid2obj[e.new_src_id].basename
                t = self.nodeid2obj[e.new_tgt_id].basename
                # If this is a palindromic loop edge from s -> -s or -s -> s,
                # then (s, t) and (-t, -s) will be the same. So don't let
                # the fact that we see (-t, -s) in inval_edgetups disqualify us
                # from saving these edges, in this particular case. (See node
                # 249210759 in the chr15_full.gv test graph for an example.)
                rev_edgetup = name_utils.negate_edge_tuple(s, t)
                if rev_edgetup == (s, t) or rev_edgetup not in inval_edgetups:
                    inval_edgetups.add((s, t))
                    # Since exactly one of the nodes of this edge will not be
                    # shown, see if we can find its reverse-complementary node
                    # in the shown nodes. Note that this reverse-complementary
                    # node might be split, which is fine.
                    if inval_type == config.INVAL_SRC:
                        rname = name_utils.negate(s)
                        rsplit = config.SPLIT_LEFT
                    else:
                        rname = name_utils.negate(t)
                        rsplit = config.SPLIT_RIGHT
                    rn = graph_utils.find_full_or_certain_split_node(
                        nodename2objs, rname, rsplit
                    )
                    if rn is None:
                        # this might be redundant with the warning from above
                        logging.warning(
                            f"Asymmetry: for {e}, {inval_type}-node {rn} not "
                            f"in {self}?"
                        )
                    elif rn.unique_id not in shown_nids:
                        raise WeirdError(f"{rn} is not shown, but {e} inval?")
                    else:
                        # okay, rn corresponds to a shown node! yay. we will
                        # draw this invalidated edge specially using it
                        inval_edges.append(
                            InvalidatedEdge(e, inval_type, rn.unique_id)
                        )

        # Record this subgraph, so that we can handle it specially
        # when drawing with the decoupling option turned on.
        self.dc_shown_node_ids = shown_nids
        self.dc_shown_edge_ids = shown_eids
        self.dc_inval_edges = inval_edges
        self.dc_shown_patt_ids = graph_utils.get_avail_pattern_ids(
            self.patterns,
            self.dc_shown_node_ids,
            self.dc_shown_edge_ids,
        )
        self.decoupling_done = True
        return True

    def to_cyjs(
        self, scope_settings, modifier_settings, layout_alg, layout_params
    ):
        """Creates Cytoscape.js elements for this subgraph.

        Parameters
        ----------
        scope_settings: list
        modifier_settings: list
            Various settings (show patterns?, do recursive layout?, etc.)

        layout_alg: str
            Layout algorithm to use.

        layout_params: dict
            Other parameters to pass to Layout, if we are calling a Graphviz
            program.

        Returns
        -------
        DrawResults
        """
        if self.decoupling_done and ui_utils.decouple(scope_settings):
            sobj = DecoupledSubgraph(self)
        else:
            sobj = self

        lay = None
        if layout_alg in ui_config.LAYOUT2GVPROG:
            lay = Layout(
                sobj,
                scope_settings,
                modifier_settings,
                layout_alg,
                layout_params,
            )
        return DrawResults({sobj: lay}, scope_settings, modifier_settings)


class DecoupledSubgraph(Subgraph):
    """Represents a decoupled subgraph.

    Um, the reason this is in this file -- and not in its own file -- is to
    avoid circular imports, since this relies on Subgraph and Subgraph relies
    on this. You could totally avoid that problem by making Subgraph defer
    importing DecoupledSubgraph until to_cyjs() gets called, but that seems
    messy and inefficient.
    """

    def __init__(self, sg):
        """Initializes this object.

        Parameters
        ----------
        sg: Subgraph
        """
        if not sg.decoupling_done:
            raise WeirdError(f"{sg} not decoupled?")

        # If sg is a Component, set the same component number for this obj --
        # so it is sorted properly by DrawResults.get_sorted_regions()
        if hasattr(sg, "cc_num"):
            self.cc_num = sg.cc_num

        # Lump shown Edges and InvalidatedEdges together, which makes
        # downstream stuff easier to think about -- less special-casing needed.
        # (We defer doing this to here in order to avoid having to store extra
        # stuff all the time, I guess ...?)
        edges = graph_utils.filter_objs_by_ids(sg.edges, sg.dc_shown_edge_ids)
        edges += sg.dc_inval_edges

        super().__init__(
            None,
            f"dc_{sg.name}",
            graph_utils.filter_objs_by_ids(sg.nodes, sg.dc_shown_node_ids),
            edges,
            graph_utils.filter_objs_by_ids(sg.patterns, sg.dc_shown_patt_ids),
            node_centric=sg.node_centric,
            length_field=sg.length_field,
            record_node_names=sg.record_node_names,
            count_positive_names=sg.count_positive_names,
        )
