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
from metagenomescope import config, layout_utils, misc_utils
from metagenomescope.errors import WeirdError


def get_ids_of_nodes(nodes):
    return [n.unique_id for n in nodes]


def verify_vr_and_nodes_good(vr, nodes):
    """Checks a Pattern's ValidationResults object and Node objects.

    Verifies that (1) the ValidationResults describes a valid pattern,
    (2) all Nodes in "nodes" have unique IDs (at least compared to each other),
    and (3) vr.nodes exactly matches "nodes".

    Returns a list of the node IDs described by these objects.
    """
    if not vr:
        raise WeirdError(
            "Can't create a Pattern from an invalid ValidationResults?"
        )

    # We only verify that the IDs described by the Nodes in "nodes" are unique
    # -- the ValidationResults constructor should have already verified that
    # its .nodes are unique.
    node_ids = get_ids_of_nodes(nodes)
    misc_utils.verify_unique(node_ids)

    if set(node_ids) != set(vr.nodes):
        raise WeirdError(f"Different node IDs: {node_ids} vs. {vr.nodes}")

    return node_ids


def verify_edges_in_induced_subgraph(edges, node_ids):
    for e in edges:
        if e.dec_src_id not in node_ids or e.dec_tgt_id not in node_ids:
            raise WeirdError(
                f"{e} not in induced subgraph of node IDs {node_ids}?"
            )


class Pattern(Node):
    """Represents a pattern in an assembly graph."""

    def __init__(
        self,
        unique_id,
        validation_results,
        nodes,
        edges,
    ):
        """Initializes this Pattern object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes, edges, and patterns in
            the assembly graph) integer ID of this pattern.

        validation_results: validators.ValidationResults
            Results from successfully validating this pattern in the assembly
            graph.

        nodes: list of Nodes
            List of all child Node objects of this pattern (including collapsed
            Patterns -- note that Pattern is a subclass of Node!). These IDs
            should exactly match those in validation_results.nodes.

        edges: list of Edges
            List of all child Edge objects of this pattern. We define an edge
            as a child of a pattern P if both its source and target node are
            contained in "nodes". (You can therefore think of "edges" as the
            edges of the "induced subgraph" of "nodes".)
        """
        self.unique_id = unique_id

        self.node_ids = verify_vr_and_nodes_good(validation_results, nodes)
        self.pattern_type = validation_results.pattern_type
        self.start_node_id = None
        self.end_node_id = None
        self.has_start_end = validation_results.has_start_end
        if self.has_start_end:
            self.start_node_id = validation_results.start_node
            self.end_node_id = validation_results.end_node

        self.nodes = nodes
        # self.nodes stores the child Node objects of this Pattern, while
        # validation_results.nodes stores these Nodes' IDs. For checking that
        # the edges are "valid", we need the Node IDs, so it's easiest to just
        # pass validation_results.nodes to check_edges_in_induced_subgraph().
        verify_edges_in_induced_subgraph(edges, validation_results.nodes)
        self.edges = edges

        # Will be filled in after performing top-level AssemblyGraph layout,
        # when self.set_bb() is called. Stored in points.
        self.left = None
        self.bottom = None
        self.right = None
        self.top = None

        # Update parent ID info for child nodes (including patterns) and edges
        for coll in (self.nodes, self.edges):
            for obj in coll:
                obj.parent_id = self.unique_id

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
        suffix = ""
        if self.has_start_end:
            suffix = f" from {self.start_node_id} to {self.end_node_id}"
        return (
            f"{config.PT2HR[self.pattern_type]} (ID {self.unique_id}) of "
            f"nodes {self.node_ids}{suffix}"
        )

    def get_counts(self):
        node_ct = 0
        edge_ct = len(self.edges)
        patt_ct = 0
        for node in self.nodes:
            if type(node) == Pattern:
                patt_ct += 1
                child_pattern_counts = node.get_counts()
                node_ct += child_pattern_counts[0]
                edge_ct += child_pattern_counts[1]
                patt_ct += child_pattern_counts[2]
            else:
                node_ct += 1

        return [node_ct, edge_ct, patt_ct]

    def set_cc_num(self, cc_num):
        """Updates the component number attribute of all Patterns, nodes, and
        edges in this Pattern.

        This is really important to keep around for later -- it allows us to
        traverse nodes/edges/etc. in the graph more easily later on.
        """
        for coll in (self.nodes, self.edges):
            for obj in coll:
                obj.set_cc_num(cc_num)
        super().set_cc_num(cc_num)

    def layout(self):
        # Recursively go through all of the nodes within this pattern. If any
        # of these isn't actually a node (and is actually a pattern), then lay
        # out that pattern!
        for node in self.nodes:
            if type(node) == Pattern:
                node.layout()

        # Now that all of the patterns (if present) within this pattern have
        # been laid out, lay out this pattern.

        gv_input = layout_utils.get_gv_header()
        # Add node info
        for node in self.nodes:
            gv_input += (
                f"\t{node.unique_id} [height={node.height},width={node.width},"
                f"shape={node.shape}];\n"
            )
        # Add edge info. Note that we don't bother passing thickness info to
        # dot, since (at least to my knowledge) it doesn't impact the layout.
        for edge in self.edges:
            gv_input += f"\t{edge.dec_src_id} -> {edge.dec_tgt_id};\n"
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
        # NOTE: for child patterns of this pattern, we don't need to update the
        # child node/edge positions within this sub-pattern just yet: we only
        # need to worry about having stuff be relative to the immediate parent
        # pattern. When the top level of each component is laid out, we can go
        # down through the patterns and update positions accordingly --
        # no need to slow ourselves down by repeatedly updating this
        # information throughout the layout process.
        for node in self.nodes:
            node = cg.get_node(node.unique_id)
            x, y = layout_utils.getxy(node.attr["pos"])
            node.relative_x = x
            node.relative_y = y

        # Extract (relative) edge control points
        for edge in self.edges:
            # TODO: This is gonna cause problems when we have parallel edges.
            # Modify the pygraphviz stuff to explicitly create nodes and edges,
            # rather than passing in a string of graphviz input -- this way we
            # can define edge keys explicitly (which prooobably won't be
            # necessary but whatevs).
            cg_edge = cg.get_edge(edge.dec_src_id, edge.dec_tgt_id)
            edge.relative_ctrl_pt_coords = layout_utils.get_control_points(
                cg_edge.attr["pos"]
            )

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

    def make_into_left_split(self):
        raise WeirdError(f"Attempted to left-split pattern {self}.")

    def make_into_right_split(self):
        raise WeirdError(f"Attempted to right-split pattern {self}.")
