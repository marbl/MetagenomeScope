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
from .. import ui_config, ui_utils
from ..layout import Layout
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

    def __init__(self, unique_id, name, nodes, edges, patterns):
        """Initializes this Subgraph object.

        Parameters
        ----------
        unique_id: int

        name: str

        nodes: list of Node

        edges: list of Edge

        patterns: list of Pattern

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

        for n in nodes:
            self._add_node(n)
        for e in edges:
            self._add_edge(e)
        for p in patterns:
            self._add_pattern(p)
        self.round_num_full_nodes()

    def _get_repr_counts(self):
        return (
            f"{self.num_total_nodes:,} node(s), "
            f"{self.num_total_edges:,} edge(s), "
            f"{self.pattern_stats.sum():,} pattern(s)"
        )

    def __repr__(self):
        return f"{self.name}: {self._get_repr_counts()}"

    def _add_node(self, node):
        self.nodes.append(node)
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
        self.num_total_edges += 1

    def _add_pattern(self, pattern):
        self.patterns.append(pattern)
        self.pattern_stats.update(pattern.pattern_type)

    def get_objs(self):
        return itertools.chain(self.nodes, self.edges, self.patterns)

    def to_cyjs(self, draw_settings, layout_alg, layout_params):
        """Creates Cytoscape.js elements for all nodes/edges in this subgraph.

        Parameters
        ----------
        draw_settings: list
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
            logging.debug(f"  Laying out {self}; settings: {draw_settings}...")
            lay = Layout(self, draw_settings, layout_alg, layout_params)
            logging.debug("  ...Done with layout!")
        return DrawResults({self: lay}, draw_settings)
