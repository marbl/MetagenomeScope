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

from .pattern_stats import PatternStats


class Component(object):
    """Represents a weakly connected component in an assembly graph."""

    def __init__(self, unique_id):
        """Initializes this Component object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other Components) integer ID of this
            Component.
        """
        self.unique_id = unique_id
        self.nodes = []
        self.edges = []
        self.patterns = []

        # Number of nodes in this Component that are not split.
        self.num_unsplit_nodes = 0

        # Number of split nodes in this Component (including both left and
        # right splits: e.g. if a component contains exactly one instance of a
        # node being split, then num_split_nodes should be 2).
        self.num_split_nodes = 0

        # Number of total nodes in this Component (should be equal to
        # num_unsplit_nodes + num_split_nodes). Note that if you'd like,
        # instead, to have the total number of "full" nodes (treating the left
        # and right split of a node as one "full" node), then that is equal to
        # num_unsplit_nodes + (num_split_nodes / 2).
        self.num_total_nodes = 0

        # Number of edges in this Component, not including fake edges from a
        # left split node to a right split node.
        self.num_real_edges = 0

        # Number of fake edges in this Component.
        self.num_fake_edges = 0

        # Total number of edges in this Component (should be equal to
        # num_real_edges + num_fake_edges).
        self.num_total_edges = 0

        # PatternStats for this Component.
        self.pattern_stats = PatternStats()

    def add_node(self, node):
        self.nodes.append(node)
        if node.is_split():
            self.num_split_nodes += 1
        else:
            self.num_unsplit_nodes += 1
        self.num_total_nodes += 1

    def add_edge(self, edge):
        self.edges.append(edge)
        if edge.is_fake:
            self.num_fake_edges += 1
        else:
            self.num_real_edges += 1
        self.num_total_edges += 1

    def add_pattern(self, pattern):
        nodes, edges, patts, patt_stats = pattern.get_descendant_info()
        for n in nodes:
            self.add_node(n)
        for e in edges:
            self.add_edge(e)
        for p in patts:
            self.patterns.append(p)
        self.pattern_stats += patt_stats
