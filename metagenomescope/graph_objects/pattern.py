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


class Pattern(object):
    def __init__(self, pattern_id, pattern_type, node_ids, subgraph):
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.node_ids = node_ids
        self.subgraph = subgraph

        # Will be filled in after calling self.layout()
        self.width = None
        self.height = None
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

        gv_input = "digraph nodegroup {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t{};\n".format(config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [{}];\n".format(config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            gv_input += "\tedge [{}];\n".format(config.GLOBALEDGE_STYLE)

        # Add node info
        for node_id in self.node_ids:
            if node_id in id2pattern:
                # If this node is a collapsed pattern, get its dimensions from
                # its Pattern object using id2pattern.
                # This is probably a pretty roundabout way of doing this but it
                # works and honestly that is all I can hope for right now. 2020
                # is such a weird year, dude.
                height = id2pattern[node_id].height
                width = id2pattern[node_id].width
                shape = id2pattern[node_id].shape
            else:
                # If this is a normal node, just get its dimensions from the
                # graph.
                data = subgraph.nodes[node_id]
                height = data["height"]
                width = data["width"]
                shape = data["shape"]
            gv_input += "\t{} [height={},width={},shape={}];\n".format(
                height, width, shape
            )

        # Add edge info. Note that we don't bother passing thickness info to
        # dot, since (at least to my knowledge) it doesn't impact the layout.
        for edge in self.subgraph.edges:
            gv_input += "\t{} -> {}\n".format(edge[0], edge[1])

        gv_input += "}"

        # Now, we can lay out this pattern's graph! Yay.
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog="dot")

        # Extract dimension info. The first two coordinates in the bounding box
        # (bb) should always be (0, 0).
        _, _, self.width, self.height = cg.graph_attr["bb"].split(",")

        # TODO: assign relative node coordinates (x and y):
        # -For each normal node in this component, assign x and y.
        # -For each pattern node in this component, assign x and y, then update
        #  its child nodes' x and y coordinates accordingly.
        #
        # Then TODO I guess we should do the same for edge control points

        # TODO: actually do layout using dot, then store bounding box,
        # width/height, and assign node relative positions. I guess we should
        # keep track of namespace issues (e.g. what if nodes actually have 'x'
        # params \._./).
        #
        # TODO: keep track of orientation for plain nodes. I guess add that to
        # the stuff stored in the nx dicts. "shape"?


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
