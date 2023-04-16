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

    It is worth noting that all Edge objects should be created either
    (1) soon after we load the input assembly graph file, or (2) whenever
    we need to "split" a node (when we add a "fake" edge from the left to
    the right split of this node).

    As we split nodes and collapse patterns in the graph, we may need to
    re-route edges. What two nodes does an edge actually connect?
    You can think of three "levels" of this:

    1. The original source and target ID of an edge. Usually, these should
       correspond to the IDs of full nodes in the input assembly graph,
       but -- if this edge is fake -- then both of these IDs should
       correspond to split nodes (the source should be the left split node,
       and the target should be the right split node).

       These attributes are controlled by the orig_src_id and orig_tgt_id
       parameters of this function, and will be stored in the identically-
       named attributes of this Edge object. These attributes should never
       be modified in an already-created Edge object.

    2. The rerouted source and target ID of an edge. These should still
       correspond to node IDs (either full nodes or split nodes); however,
       they should be changed as we perform node splitting. For example, if
       an edge points from node 1 to node 2, but node 2 gets split into
       nodes 3 and 4, then the edge should be rerouted to point from node
       1 to node 3.

       Note that we still don't have any conception of "patterns" at this
       level. If you draw out all the edges in the graph at this level
       (and just the nodes that they are incident on), then you'd see the
       original graph -- albeit with some nodes replaced by their two split
       nodes.

       These attributes are controlled by the new_src_id and new_tgt_id
       parameters of this function. You can update them using the
       reroute_src() and reroute_tgt() methods, respectively.

    3. The rerouted source and target ID of an edge, in the decomposed
       graph. If this edge's (rerouted) source and target node are not
       children of any patterns -- or, if the source and target node are
       children of the same pattern -- then these IDs should be identical
       to the previous level's IDs. However, if neither of these conditions
       holds, then at least one of these attributes should be updated to a
       pattern "node"'s ID as we collapse patterns in the graph. (These
       attributes represent the topology of the decomposed graph.)

       These attributes are controlled by the dec_src_id and dec_tgt_id
       parameters of this function. You can update them using the
       reroute_dec_src() and reroute_dec_tgt() methods, respectively.
    """

    def __init__(
        self,
        unique_id,
        orig_src_id,
        orig_tgt_id,
        is_fake,
        is_outlier=None,
        relative_weight=None,
    ):
        """Initializes this Edge object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other edges in the assembly graph)
            integer ID of this edge.

        orig_src_id: int
            Unique ID parameter of the original source node of this edge. By
            "original," I mean that this ID should correspond to the unique_id
            parameter of an actual Node object (which may or may not be a split
            Node). It shouldn't point to a pattern.

        orig_tgt_id: int
            Unique ID parameter of the original target node of this edge. See
            the orig_src_id description.

        is_fake: bool
            If False, this indicates that this edge connects two distinct nodes.
            If True, this indicates that this edge connects a left and right
            split node (i.e. orig_src_id and orig_tgt_id are both split nodes).

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
        self.orig_src_id = orig_src_id
        self.orig_tgt_id = orig_tgt_id
        self.is_fake = is_fake
        self.is_outlier = is_outlier
        self.relative_weight = relative_weight

        self.new_src_id = orig_src_id
        self.new_tgt_id = orig_tgt_id

        self.dec_src_id = orig_src_id
        self.dec_tgt_id = orig_tgt_id

        self.ctrl_pt_coords = None
        self.relative_ctrl_pt_coords = None
        self.parent_id = None

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

    def reroute_src(self, new_src_id):
        self.new_src_id = new_src_id

    def reroute_tgt(self, new_tgt_id):
        self.new_tgt_id = new_tgt_id

    def reroute_dec_src(self, dec_src_id):
        self.dec_src_id = dec_src_id

    def reroute_dec_tgt(self, dec_tgt_id):
        self.dec_tgt_id = dec_tgt_id
