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
from .pattern_stats import PatternStats
from metagenomescope import config, layout_utils, misc_utils
from metagenomescope.errors import WeirdError


def get_ids_of_nodes(nodes):
    return [n.unique_id for n in nodes]


def is_pattern(obj):
    return type(obj) == Pattern


def verify_vr_and_nodes_good(vr, nodes):
    """Checks a Pattern's ValidationResults object and Node objects.

    Verifies that (1) the ValidationResults describes a valid pattern,
    (2) all Nodes in "nodes" have unique IDs (at least compared to each other),
    and (3) vr.nodes exactly matches "nodes".
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

    if set(node_ids) != set(vr.node_ids):
        raise WeirdError(f"Different node IDs: {node_ids} vs. {vr.node_ids}")


def verify_edges_in_induced_subgraph(edges, node_ids):
    for e in edges:
        if e.dec_src_id not in node_ids or e.dec_tgt_id not in node_ids:
            raise WeirdError(
                f"{e} not in induced subgraph of node IDs {node_ids}?"
            )


def verify_1_node(node_ids, node_type):
    if len(node_ids) != 1:
        raise WeirdError(f"Not exactly 1 {node_type} node: {node_ids}?")


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
            Patterns -- note that Pattern is a subclass of Node!). The IDs of
            these Nodes should exactly match those in
            validation_results.node_ids.

        edges: list of Edges
            List of all child Edge objects of this pattern. We define an edge
            as a child of a pattern P if both its source and target node are
            contained in "nodes". (You can therefore think of "edges" as the
            edges of the "induced subgraph" of "nodes".)
        """
        self.unique_id = unique_id

        verify_vr_and_nodes_good(validation_results, nodes)
        self.pattern_type = validation_results.pattern_type
        self.start_node_ids = validation_results.start_node_ids
        self.end_node_ids = validation_results.end_node_ids

        self.nodes = nodes
        verify_edges_in_induced_subgraph(edges, validation_results.node_ids)
        self.edges = edges

        # Will be filled in after performing top-level AssemblyGraph layout,
        # when self.set_bb() is called. Stored in points.
        self.left = None
        self.bottom = None
        self.right = None
        self.top = None

        # Update parent ID info for child nodes (including patterns) and edges
        self.merged_child_chains = []
        is_chain_ish = (
            self.pattern_type == config.PT_CHAIN
            or self.pattern_type == config.PT_CYCLICCHAIN
        )
        # Iterate through a copy of self.nodes, since we may remove merged
        # chain nodes from self.nodes (and removing from a list while iterating
        # through it will cause weird behavior).
        for node in self.nodes[:]:
            node.parent_id = self.unique_id
            if (
                is_chain_ish
                and is_pattern(node)
                and node.pattern_type == config.PT_CHAIN
            ):
                self._absorb_child_pattern(node)
        for edge in self.edges:
            edge.parent_id = self.unique_id

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
        return (
            f"{config.PT2HR[self.pattern_type]} {self.unique_id} of "
            f"nodes {self.get_node_ids()} from {self.start_node_ids} to "
            f"{self.end_node_ids}"
        )

    def _absorb_child_pattern(self, child_pattern):
        """Merges a child Pattern's contents into this Pattern.

        As of writing, this should only be applied if child_pattern is a chain
        (and this Pattern, i.e. "self," is a chain or cyclic chain).

        Note that this method has no conception of the AssemblyGraph in which
        these Patterns are contained: you'll need to reroute edges that point
        to parts of this child pattern manually.
        """
        # (This attr is set to False by default in the Node constructor)
        child_pattern.removed = True
        for node in child_pattern.nodes:
            node.parent_id = self.unique_id
            self.nodes.append(node)
        for edge in child_pattern.edges:
            edge.parent_id = self.unique_id
            self.edges.append(edge)

        # there should never be a case where node is both the start
        # and end of this new pattern, but let's be safe anyway
        verify_1_node(self.start_node_ids, "start")
        verify_1_node(self.end_node_ids, "end")
        verify_1_node(child_pattern.start_node_ids, "start")
        verify_1_node(child_pattern.end_node_ids, "end")
        if self.start_node_ids[0] == child_pattern.unique_id:
            self.start_node_ids = [child_pattern.start_node_ids[0]]
        if self.end_node_ids[0] == child_pattern.unique_id:
            self.end_node_ids = [child_pattern.end_node_ids[0]]

        self.nodes.remove(child_pattern)
        self.merged_child_chains.append(child_pattern)

    def get_node_ids(self):
        return get_ids_of_nodes(self.nodes)

    def get_counts(self):
        node_ct = 0
        edge_ct = len(self.edges)
        patt_ct = 0
        for node in self.nodes:
            if is_pattern(node):
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

    def to_dot(self):
        gv = (
            f"subgraph cluster_{config.PT2HR[self.pattern_type]}_"
            f"{self.unique_id} {{\n"
        )
        gv += '\tstyle="filled";\n'
        gv += f'\tfillcolor="{config.PT2COLOR[self.pattern_type]}";\n'
        for node in self.nodes:
            # Since both Nodes and Patterns have their own to_dot() methods, we
            # actually don't need to distinguish between them here :D
            gv += node.to_dot()
        for edge in self.edges:
            gv += edge.to_dot()
        gv += "}\n"
        return gv

    def layout(self):
        gv_input = layout_utils.get_gv_header()
        # Recursively go through all of the nodes within this pattern. If any
        # of these isn't actually a node (and is actually a pattern), then lay
        # out that pattern!
        for node in self.nodes:
            if is_pattern(node):
                node.layout()
                # TODO: add a "solid" parameter to Pattern.to_dot() or
                # something that just converts this child pattern to a
                # rectangle here (rather than representing it as a subgraph) --
                # then use this.
                gv_input += node.to_dot()
            else:
                gv_input += node.to_dot(label=False, lr=False)
        for edge in self.edges:
            gv_input += edge.to_dot(level="dec")
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

    def get_pattern_stats(self):
        """Gets stats about how many types of each pattern are contained here.

        Note that these include this pattern (i.e. calling this method on a
        "bottom-level" bubble pattern will indicate that there is 1 bubble
        here).

        Returns
        -------
        PatternStats
        """
        stats = PatternStats()
        if self.pattern_type == config.PT_BUBBLE:
            stats.num_bubbles += 1
        elif self.pattern_type == config.PT_CHAIN:
            stats.num_chains += 1
        elif self.pattern_type == config.PT_CYCLICCHAIN:
            stats.num_cyclicchains += 1
        elif self.pattern_type == config.PT_FRAYEDROPE:
            stats.num_frayedropes += 1
        else:
            raise WeirdError(f"Unrecognized pattern type: {self.pattern_type}")

        for node in self.nodes:
            if is_pattern(node):
                stats += node.get_pattern_stats()

        return stats
