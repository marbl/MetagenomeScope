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


from metagenomescope.layout import layout_config, layout_utils
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

    1. The ORIGINAL source and target ID of an edge. Usually these should
       correspond to the IDs of full nodes in the input assembly graph.

       These attributes are controlled by the orig_src_id and orig_tgt_id
       parameters of this function, and will be stored in the identically-
       named attributes of this Edge object. These attributes should never
       be modified in an already-created Edge object.

       Note that, if this edge is fake, then these IDs should correspond to
       split nodes (the source should be the left split node, and the target
       should be the right split node) -- because a fake edge has no original
       "full" node, by design. However, for non-fake edges, these IDs will
       remain static, even if the nodes they point to end up being split or
       whatever.

       We keep this information around solely for debugging / for reference, as
       of 2025 -- it does not look like these properties are actually used to
       make any decisions. As the above text implies, performing decomposition
       (and splitting nodes, etc.) will make these IDs obsolete. The two levels
       below are more useful for actually drawing the graph.

    2. The REROUTED source and target ID of an edge. These should still
       correspond to non-pattern node IDs (either full nodes or split nodes);
       however, they will be changed as we perform node splitting. For example,
       if an edge E points from node 1 to node 2, and we determine that node 2
       is the starting node of a pattern (so it gets split into 2-L ==> 2-R),
       then E should be rerouted to point from node 1 to node 2-L.

       (This is assuming that node 2's pattern doesn't contain node 1. If it
       did, then we'd route the edge from node 1 to node 2-R. Although it's
       worth keeping in mind that currently, node splitting is lazy and only
       creates one "real" node [for the external half of the split], so node 2
       should just be renamed to 2-R -- it'll keep the same ID. Node 2-L would
       have a new ID, though.)

       Note that we still don't have any conception of "patterns" at this
       level. If you draw out all the edges in the graph at this level
       (and just the nodes that they are incident on), then you'd see the
       original graph -- albeit with some split nodes and fake edges. This
       should match the topology of the .graph attribute of the AssemblyGraph
       object containing this Edge.

       These attributes are controlled by the new_src_id and new_tgt_id
       parameters of this function. You can update them using the
       reroute_src() and reroute_tgt() methods, respectively.

    3. The REROUTED source and target ID of an edge, IN THE DECOMPOSED
       GRAPH. If this edge's (rerouted) source and target node are not
       children of any patterns -- or, if the source and target node are
       children of the same pattern -- then these IDs should be identical
       to the previous level's IDs. However, if neither of these conditions
       hold, then at least one of these attributes should have been updated
       to a pattern "node"'s ID as we collapse patterns in the graph.

       This should match the topology of the .decomposed_graph attribute of the
       AssemblyGraph object containing this Edge, although you might need to
       search through the colllapsed pattern nodes in that graph to reach
       this particular edge.

       These attributes are controlled by the dec_src_id and dec_tgt_id
       parameters of this function. You can update them using the
       reroute_dec_src() and reroute_dec_tgt() methods, respectively.
    """

    def __init__(
        self, unique_id, orig_src_id, orig_tgt_id, data, is_fake=False
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

        data: dict
            Maps field names (e.g. "length", "multiplicity", ...) to their
            values for this edge. The amount of this data will vary based
            on the input assembly graph's filetype and if this edge is fake
            (if no data is available for this edge, this can be an empty dict).

        is_fake: bool
            If False, this indicates that this edge connects two distinct nodes.
            If True, this indicates that this edge connects a left and right
            split node (i.e. orig_src_id and orig_tgt_id are both split nodes).
        """
        self.unique_id = unique_id
        self.orig_src_id = orig_src_id
        self.orig_tgt_id = orig_tgt_id
        self.data = data
        self.is_fake = is_fake

        self.new_src_id = orig_src_id
        self.new_tgt_id = orig_tgt_id

        self.dec_src_id = orig_src_id
        self.dec_tgt_id = orig_tgt_id

        self.prev_dec_src_id = orig_src_id
        self.prev_dec_tgt_id = orig_tgt_id

        self.ctrl_pt_coords = None
        self.relative_ctrl_pt_coords = None

        # for random coloring
        self.rand_idx = None

        # ID of the pattern containing this edge, or None if this edge
        # exists in the top level of the graph. Note that some edges may
        # connect nodes that are in different patterns (in the uncollapsed
        # graph), or -- in the collapsed graph -- different pattern nodes.
        # You can thus think of the parent pattern of an edge as the "least
        # common ancestor" pattern that contains both of an edge's nodes (or
        # None if at least one of this edge's nodes is not in a pattern).
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this edge.
        self.cc_num = None

    def __repr__(self):
        # Add on a little symbol to let us know that an edge is fake. Useful in
        # debugging.
        if self.is_fake:
            suffix = "*"
        else:
            suffix = " "
        return (
            f"Edge{suffix}{self.unique_id} (orig: {self.orig_src_id} -> "
            f"{self.orig_tgt_id}; new: {self.new_src_id} -> "
            f"{self.new_tgt_id}; dec: {self.dec_src_id} -> "
            f"{self.dec_tgt_id})"
        )

    def reroute_src(self, new_src_id):
        self.new_src_id = new_src_id

    def reroute_tgt(self, new_tgt_id):
        self.new_tgt_id = new_tgt_id

    def reroute_dec_src(self, dec_src_id):
        self.prev_dec_src_id = self.dec_src_id
        self.dec_src_id = dec_src_id

    def reroute_dec_tgt(self, dec_tgt_id):
        self.prev_dec_tgt_id = self.dec_tgt_id
        self.dec_tgt_id = dec_tgt_id

    def revert_dec_src(self):
        if self.prev_dec_src_id is not None:
            self.dec_src_id = self.prev_dec_src_id
            self.prev_dec_src_id = None
        else:
            # we can support this if needed but i don't thiiiink it should ever
            # happen
            raise WeirdError(f"Tried to revert dec. src. twice for {self}?")

    def revert_dec_tgt(self):
        if self.prev_dec_tgt_id is not None:
            self.dec_tgt_id = self.prev_dec_tgt_id
            self.prev_dec_tgt_id = None
        else:
            raise WeirdError(f"Tried to revert dec. tgt. twice for {self}?")

    def set_cc_num(self, cc_num):
        self.cc_num = cc_num

    def has_userspecified_id(self):
        return "id" in self.data

    def get_userspecified_id(self):
        if self.has_userspecified_id():
            return self.data["id"]
        else:
            raise WeirdError(f"No 'id' field for {self}. Data: {self.data}")

    def to_dot(self, level="new", indent=layout_config.INDENT):
        if level == "dec":
            src = self.dec_src_id
            tgt = self.dec_tgt_id
        elif level == "new":
            src = self.new_src_id
            tgt = self.new_tgt_id
        else:
            raise WeirdError(f"Unrecognized edge level: {level}")
        return layout_utils.get_edge_dot(src, tgt, self.is_fake, indent)

    def to_cyjs(self, incl_patterns=True):
        ele = {
            "data": {
                "source": str(self.new_src_id),
                "target": str(self.new_tgt_id),
                "uid": self.unique_id,
            },
            "classes": f"edgerand{self.rand_idx}",
        }
        # pass LJA / Flye edge IDs to the viz, for selection / etc
        if self.has_userspecified_id():
            # NOTE: "id" has a special meaning in Cytoscape.js, and if
            # we use "id" here then this overwrites that and causes weird
            # problems in the viz. So just use something generic instead
            ele["data"]["edgeID"] = self.get_userspecified_id()

        if incl_patterns and self.parent_id is not None:
            ele["data"]["parent"] = str(self.parent_id)
        if self.is_fake:
            ele["classes"] += " fake"
        return ele
