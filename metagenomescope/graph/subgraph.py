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

import itertools
from .. import ui_config, ui_utils, name_utils
from ..layout import Layout
from ..errors import WeirdError
from .pattern_stats import PatternStats
from .draw_results import DrawResults


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

        # maps pattern IDs to objects. Useful if we want to e.g. figure out
        # what type of pattern an edge has (relevant to
        # layout_utils.flatten_some_edges()).
        self.pattid2obj = {}

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

    def to_cyjs(
        self, scope_settings, modifier_settings, layout_alg, layout_params
    ):
        """Creates Cytoscape.js elements for all nodes/edges in this subgraph.

        Parameters
        ----------
        scope_settings: list
        modifier_settings: list
            Various draw settings (show patterns?, do recursive layout?, etc.)

        layout_alg: str
            Layout algorithm to use.

        layout_params: dict
            Other parameters to pass to Layout, if we are calling a Graphviz
            program.

        Returns
        -------
        DrawResults
        """
        lay = None
        if layout_alg in ui_config.LAYOUT2GVPROG:
            lay = Layout(
                self,
                scope_settings,
                modifier_settings,
                layout_alg,
                layout_params,
            )
        return DrawResults({self: lay}, scope_settings)
