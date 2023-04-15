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


from metagenomescope.errors import WeirdError

class Edge(object):
    """Represents an edge in an assembly graph.

    Similarly to the Node class, Edges can have wildly varying amounts of data
    depending on the input graph.
    """
    def __init__(self, unique_id, src_id, tgt_id, is_fake, is_outlier=None, relative_weight=None):
        """Initializes this edge object.

        As we decompose the graph during the pattern identification process, we
        can re-route 

        TODO add also non-orig src/tgt attrs

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other edges in the assembly graph)
            integer ID of this edge.

        orig_src_id: int
            Unique ID parameter of the original source node of this edge. (By
            "original," I mean in the original input graph: if this is a fake
            edge, then )

        orig_tgt_id: int
            Unique ID parameter of the original target node of this edge.

        is_fake: bool
            If True, this indicates that this edge connects two distinct nodes.
            If False, this indicates that this edge connects a left and right
            split node.

        is_outlier: int
            One of {-1, 0, 1}. -1 indicates that this edge is a low outlier; 0
            indicates that this edge is not an outlier (either because its
            coverage is in the middle, or because the graph doesn't have edge
            multiplicities); 1 indicates that this edge is a high outlier.

        relative_weight: float
            In the range [0, 1]. See AssemblyGraph.scale_edges() for details
            (I'm probably gonna deprecate doing this in Python eventually
            anyway)...
        """
        self.unique_id = unique_id
        self.src_id = src_id
        self.tgt_id = tgt_id
        self.is_fake = is_fake
        self.is_outlier = is_outlier
        self.relative_weight = relative_weight

        self.ctrl_pt_coords = None
        self.relative_ctrl_pt_coords = None
        self.parent_id = None
        self.



        # Relative position of this node within its parent pattern, if this
        # node is located within a pattern. (None if this node exists in the
        # top level of the graph.) Stored in points.
        self.relative_x = None
        self.relative_y = None

        # Absolute position of this node within its connected component.
        self.x = None
        self.y = None

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        self.cc_num = None

        # Extra data fields from the input -- can be located in the assembly
        # graph file (e.g. GC content, if this node corresponds to a sequence
        # and we have access to this sequence), and eventually should be
        # generalized to other metadata files
        # (https://github.com/marbl/MetagenomeScope/issues/243).
        self.extra_data = {}

    def __repr__(self):
        return f"Node {self.unique_id}"

    def add_extra_data(self, key, value):
        if key in self.extra_data:
            raise WeirdError(
                f"Key {key} is already present in the extra data for node "
                f"{self.unique_id}?"
            )
        self.extra_data[key] = value
