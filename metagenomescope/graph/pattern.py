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


import pygraphviz
from .node import Node
from metagenomescope import config, layout_utils
from metagenomescope.errors import WeirdError


def check_vr(vr):
    if not vr:
        raise WeirdError(
            "Can't create a Pattern from False ValidationResults?"
        )


class Pattern(Node):
    """Represents a pattern in an assembly graph."""

    def __init__(
        self,
        unique_id,
        pattern_type,
        validation_results,
        subgraph,
        asm_graph,
    ):
        """Initializes this Pattern object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes, edges, and patterns in
            the assembly graph) integer ID of this pattern.

        pattern_type: str
            Type of this pattern. Should be one of the config.PT_* variables
            (e.g. config.PT_BUBBLE) -- at the very least, this should have an
            entry in PT2HR.

        validation_results: validators.ValidationResults
            Results from successfully validating this pattern in the assembly
            graph.

        subgraph: nx.MultiDiGraph
            Induced subgraph of the nodes (including collapsed patterns) and
            edges in this pattern. TODO: do we need to have this here...?
            Couldn't we just save the reference to the AssemblyGraph?

        asm_graph: assembly_graph.AssemblyGraph
            Reference to the assembly graph to which this pattern is being
            added.
        """
        self.unique_id = unique_id
        self.pattern_type = pattern_type
        self.subgraph = subgraph

        check_vr(validation_results)
        if validation_results.has_start_end:
            self.start_node = validation_results.start_node
            self.end_node = validation_results.end_node
        else:
            self.start_node = None
            self.end_node = None
        self.node_ids = validation_results.nodes

        # Will be filled in after performing top-level AssemblyGraph layout,
        # when self.set_bb() is called. Stored in points.
        self.left = None
        self.bottom = None
        self.right = None
        self.top = None

        # Update parent ID info for child patterns, nodes, and edges
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.pattid2obj[node_id].parent_id = self.unique_id
            else:
                asm_graph.nodeid2obj[node_id].parent_id = self.unique_id
        for edge in self.subgraph.edges:
            asm_graph.edgeid2obj[edge["id"]].parent_id = self.unique_id

        # This is the shape used for this pattern during layout. In the actual
        # end visualization we might use different shapes for collapsed
        # patterns (e.g. hexagons for bubbles, hourglasses for frayed ropes),
        # but these should take up space that is a subset of the space taken up
        # by the rectangle, so just using a rectangle for layout should be ok.
        self.shape = "rectangle"

        # Use the Node constructor to initialize the rest of the stuff we need
        # for this pattern (width, height, etc.)
        #
        # For now, we just set this pattern's "name" as a string version of its
        # unique ID. I don't think we'll pass this on to the visualization
        # interface for patterns, so it doesn't really matter -- but maybe we
        # can eventually make these names fancy (e.g. "Bubble #50").
        super().__init__(unique_id, str(unique_id), {})

    def __repr__(self):
        return "{} (ID {}) of nodes {}".format(
            self.pattern_type, self.unique_id, self.node_ids
        )

    def get_counts(self, asm_graph):
        node_ct = 0
        edge_ct = len(self.subgraph.edges)
        patt_ct = 0
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                patt_ct += 1
                counts = asm_graph.pattid2obj[node_id].get_counts(asm_graph)
                node_ct += counts[0]
                edge_ct += counts[1]
                patt_ct += counts[2]
            else:
                node_ct += 1

        return [node_ct, edge_ct, patt_ct]

    def set_cc_num(self, asm_graph, cc_num):
        """Updates the component number attribute of all Patterns, nodes, and
        edges in this Pattern.

        This is really important to keep around for later -- it allows us to
        traverse nodes/edges/etc. in the graph more easily later on.
        """
        self.cc_num = cc_num
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.pattid2obj[node_id].set_cc_num(asm_graph, cc_num)
            else:
                asm_graph.nodeid2obj[node_id].cc_num = cc_num
        for edge in self.subgraph.edges:
            asm_graph.edgeid2obj[edge["id"]].cc_num = cc_num

    def layout(self, asm_graph):
        # Recursively go through all of the nodes within this pattern. If any
        # of these isn't actually a node (and is actually a pattern), then lay
        # out that pattern!
        pattid2obj = {}
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.pattid2obj[node_id].layout(asm_graph)
                pattid2obj[node_id] = asm_graph.pattid2obj[node_id]

        # Now that all of the patterns (if present) within this pattern have
        # been laid out, lay out this pattern.

        gv_input = layout_utils.get_gv_header()

        # Add node info
        for node_id in self.node_ids:
            if node_id in pattid2obj:
                # If this node is a collapsed pattern, get its dimensions from
                # its Pattern object using pattid2obj.
                # This is a pretty roundabout way of doing this but it works
                # and honestly that is all I can hope for right now. Out of all
                # the years that have happened, 2020 certainly is one of them.
                height = pattid2obj[node_id].height
                width = pattid2obj[node_id].width
                shape = pattid2obj[node_id].shape
            else:
                # If this is a normal node, get its dimensions from the
                # graph. Shape is based on the node's orientation, which should
                # also be stored in the graph.
                data = asm_graph.graph.nodes[node_id]
                height = data["height"]
                width = data["width"]
                shape = config.NODE_ORIENTATION_TO_SHAPE[data["orientation"]]
            gv_input += "\t{} [height={},width={},shape={}];\n".format(
                node_id, height, width, shape
            )

        # Add edge info. Note that we don't bother passing thickness info to
        # dot, since (at least to my knowledge) it doesn't impact the layout.
        for edge in self.subgraph.edges:
            gv_input += "\t{} -> {};\n".format(edge[0], edge[1])

        gv_input += "}"

        # Now, we can lay out this pattern's graph! Yay.
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog="dot")

        # Extract dimension info. The first two coordinates in the bounding box
        # (bb) should always be (0, 0).
        # The width and height we store here are large enough in order to
        # contain the layout of the nodes/edges/other patterns in this pattern.
        self.width, self.height = layout_utils.get_bb_x2_y2(
            cg.graph_attr["bb"]
        )

        # Extract relative node coordinates (x and y)
        for node_id in self.node_ids:
            node = cg.get_node(node_id)
            x, y = layout_utils.getxy(node.attr["pos"])
            if node_id in pattid2obj:
                # Assign x and y for this pattern.
                #
                # We should not need to _update_ the child node/edge positions
                # within this sub-pattern just yet: we only need to worry about
                # having stuff be relative to the immediate parent pattern.
                # When the top level of each component is laid out, we can go
                # down through the patterns and update positions accordingly --
                # no need to slow ourselves down by repeatedly updating this
                # information throughout the layout process.
                pattid2obj[node_id].relative_x = x
                pattid2obj[node_id].relative_y = y
            else:
                asm_graph.graph.nodes[node_id]["relative_x"] = x
                asm_graph.graph.nodes[node_id]["relative_y"] = y

        # Extract (relative) edge control points
        for edge in self.subgraph.edges:
            cg_edge = cg.get_edge(*edge)
            coords = layout_utils.get_control_points(cg_edge.attr["pos"])
            asm_graph.edgeid2obj[edge["id"]].relative_ctrl_pt_coords = coords

    def set_bb(self, x, y):
        """Given a center position of this Pattern, sets its bounding box.

        This assumes that x and y are both given in points, since the width and
        height of this pattern are both stored in points.
        """
        half_w = (self.width * config.POINTS_PER_INCH) / 2
        half_h = (self.height * config.POINTS_PER_INCH) / 2
        self.left = x - half_w
        self.right = x + half_w
        self.bottom = y - half_h
        self.top = y + half_h
