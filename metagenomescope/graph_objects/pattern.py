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
    def __init__(
        self, pattern_id, pattern_type, node_ids, subgraph, asm_graph
    ):
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.node_ids = node_ids
        self.subgraph = subgraph

        # Will be filled in after calling self.layout(). Stored in points.
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

        # ID of the pattern containing this pattern, or None if this pattern
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this pattern
        # and its child nodes/edges. Will be set in layout().
        self.cc_num = None

        # Update parent ID info for child nodes, patterns, and edges
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.id2pattern[node_id].parent_id = self.pattern_id
            else:
                asm_graph.digraph.nodes[node_id]["parent_id"] = self.pattern_id

        for edge in self.subgraph.edges:
            self.subgraph.edges[edge]["parent_id"] = self.pattern_id

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

    def set_cc_num(self, asm_graph, cc_num):
        """Updates the component number attribute of all Patterns, nodes, and
        edges in this Pattern.

        This is really important to keep around for later -- it allows us to
        traverse nodes/edges/etc. in the graph more easily later on.
        """
        self.cc_num = cc_num
        for node_id in self.node_ids:
            if asm_graph.is_pattern(node_id):
                asm_graph.id2pattern[node_id].set_cc_num(asm_graph, cc_num)
            else:
                asm_graph.digraph.nodes[node_id]["cc_num"] = cc_num
        for edge in self.subgraph.edges:
            self.subgraph.edges[edge]["cc_num"] = cc_num

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

        cg.draw("pattern{}.xdot".format(self.pattern_id), format="xdot")

        # Extract dimension info. The first two coordinates in the bounding box
        # (bb) should always be (0, 0).
        # The width and height we store here are large enough in order to
        # contain the layout of the nodes/edges/other patterns in this pattern.
        self.width, self.height = layout_utils.get_bb_x2_y2(
            cg.graph_attr["bb"]
        )
        print(
            "Pattern {} has w/h of {}, {}".format(
                self.pattern_id, self.width, self.height
            )
        )

        # Extract relative node coordinates (x and y)
        for node_id in self.node_ids:
            node = cg.get_node(node_id)
            x, y = layout_utils.getxy(node.attr["pos"])
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
                id2pattern[node_id].relative_x = x
                id2pattern[node_id].relative_y = y
            else:
                asm_graph.digraph.nodes[node_id]["relative_x"] = x
                asm_graph.digraph.nodes[node_id]["relative_y"] = y
                print(
                    "Node {} at relative x,y of {}, {} :omg:".format(
                        node_id, x, y
                    )
                )

        # Extract (relative) edge control points
        for edge in self.subgraph.edges:
            cg_edge = cg.get_edge(*edge)
            coords = layout_utils.get_control_points(cg_edge.attr["pos"])
            self.subgraph.edges[edge]["relative_ctrl_pt_coords"] = coords

    def set_bb(self, x, y):
        """Given a center position of this Pattern, sets its bounding box.

        This assumes that x and y are both given in points, since the width and
        height of this pattern are both stored in points.
        """
        print(
            "pattern {}: x, y are {}, {}, and w, h are {}, {}".format(
                self.pattern_id, x, y, self.width, self.height
            )
        )
        half_w = (self.width * config.POINTS_PER_INCH) / 2
        half_h = (self.height * config.POINTS_PER_INCH) / 2
        self.left = x - half_w
        self.right = x + half_w
        self.bottom = y - half_h
        self.top = y + half_h


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
        asm_graph,
    ):
        # NOTE: not recursive, but for now this is ok since at no point can
        # another pattern be the "real" start/end node of a bubble.
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        super().__init__(
            pattern_id, pattern_type, node_ids, subgraph, asm_graph
        )

    def get_start_node(self):
        return self.start_node_id

    def get_end_node(self):
        return self.end_node_id
