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
from metagenomescope import config, layout_utils


class Pattern(object):
    def __init__(self, pattern_id, pattern_type, node_ids, subgraph):
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.node_ids = node_ids
        self.subgraph = subgraph

        # Will be filled in after calling self.layout(). Stored in inches.
        self.width = None
        self.height = None

        # Will be filled in after either the parent pattern of this pattern is
        # laid out, or the entire graph is laid out (if this pattern has no
        # parent). Stored in points.
        self.relative_x = None
        self.relative_y = None

        # Will be filled in after performing top-level AssemblyGraph layout,
        # when self.set_bb() is called. Stored in points.
        self.left = None
        self.bottom = None
        self.right = None
        self.top = None

        # This is the shape used for this pattern during layout. In the actual
        # end visualization we might use different shapes for collapsed
        # patterns (e.g. hexagons for bubbles, hourglasses for frayed ropes),
        # but these should take up space that is a subset of the space taken up
        # by the rectangle, so just using a rectangle for layout should be ok.
        self.shape = "rectangle"

    def __repr__(self):
        return "{} (ID {}) of nodes {}".format(
            self.pattern_type, self.pattern_id, self.node_ids
        )

    def get_counts(self, asm_graph):
        node_ct = 0
        edge_ct = len(self.subgraph.edges)
        patt_ct = 0
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                patt_ct += 1
                counts = asm_graph.id2pattern[node_id].get_counts(asm_graph)
                node_ct += counts[0]
                edge_ct += counts[1]
                patt_ct += counts[2]
            else:
                node_ct += 1

        return [node_ct, edge_ct, patt_ct]

    def layout(self, asm_graph):
        # Recursively go through all of the nodes within this pattern. If any
        # of these isn't actually a node (and is actually a pattern), then lay
        # out that pattern!
        id2pattern = {}
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.id2pattern[node_id].layout(asm_graph)
                id2pattern[node_id] = asm_graph.id2pattern[node_id]

        # Now that all of the patterns (if present) within this pattern have
        # been laid out, lay out this pattern.

        gv_input = layout_utils.get_gv_header()

        # Add node info
        for node_id in self.node_ids:
            if node_id in id2pattern:
                # If this node is a collapsed pattern, get its dimensions from
                # its Pattern object using id2pattern.
                # This is a pretty roundabout way of doing this but it works
                # and honestly that is all I can hope for right now. Out of all
                # the years that have happened, 2020 certainly is one of them.
                height = id2pattern[node_id].height
                width = id2pattern[node_id].width
                shape = id2pattern[node_id].shape
            else:
                # If this is a normal node, get its dimensions from the
                # graph. Shape is based on the node's orientation, which should
                # also be stored in the graph.
                data = asm_graph.digraph.nodes[node_id]
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
        bb_split = cg.graph_attr["bb"].split(",")
        self.width = float(bb_split[2]) / config.POINTS_PER_INCH
        self.height = float(bb_split[3]) / config.POINTS_PER_INCH

        # Extract relative node coordinates (x and y)
        for node_id in self.node_ids:
            node = cg.get_node(node_id)
            pos = node.attr["pos"].split(",")
            if node_id in id2pattern:
                # Assign x and y for this pattern.
                #
                # We should not need to _update_ the child node/edge positions
                # within this sub-pattern just yet: we only need to worry about
                # having stuff be relative to the immediate parent pattern.
                # When the top level of each component is laid out, we can go
                # down through the patterns and update positions accordingly --
                # no need to slow ourselves down by repeatedly updating this
                # information throughout the layout process.
                id2pattern[node_id].relative_x = pos[0]
                id2pattern[node_id].relative_y = pos[1]
            else:
                asm_graph.digraph.nodes[node_id]["relative_x"] = pos[0]
                asm_graph.digraph.nodes[node_id]["relative_y"] = pos[1]

        # Extract (relative) edge control points
        for edge in self.subgraph.edges:
            cg_edge = cg.get_edge(*edge)
            # When it comes to associating edges with their "original"
            # start/end node, I think it'd be easiest to store these originals
            # as edge data attrs rather than using the "comment" hack from
            # earlier.
            coords = layout_utils.get_control_points(cg_edge.attr["pos"])
            self.subgraph.edges[edge]["relative_ctrl_pt_coords"] = coords

    def set_bb(x, y):
        """Given a center position of this Pattern, sets its bounding box."""
        half_w_pts = (self.width / 2) * config.POINTS_PER_INCH
        half_h_pts = (self.height / 2) * config.POINTS_PER_INCH
        self.left = x - half_w_pts
        self.right = x + half_w_pts
        self.bottom = y - half_h_pts
        self.top = y + half_h_pts


class StartEndPattern(Pattern):
    """A more specific Pattern with defined individual start/end nodes.

    Mostly used for bubbles right now, but could be used with certain
    additional types of Patterns too (e.g. chains).
    """

    def __init__(
        self,
        pattern_id,
        pattern_type,
        node_ids,
        start_node_id,
        end_node_id,
        subgraph,
    ):
        # NOTE: not recursive, but for now this is ok since at no point can
        # another pattern be the "real" start/end node of a bubble.
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        super().__init__(pattern_id, pattern_type, node_ids, subgraph)

    def get_start_node(self):
        return self.start_node_id

    def get_end_node(self):
        return self.end_node_id
