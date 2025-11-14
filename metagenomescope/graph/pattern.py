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
    return type(obj) is Pattern


def verify_vr_and_nodes_good(vr, nodes):
    """Checks a Pattern's ValidationResults object and Node objects.

    Verifies that:
    (1) the ValidationResults describes a valid pattern,
    (2) all Nodes in "nodes" have unique IDs (at least compared to each other),
    and
    (3) vr.nodes exactly matches "nodes".
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

        # we'll set this later, after pattern detection
        self.cc_num = None

        # This is the shape used for this pattern during layout. In the actual
        # end visualization we might use different shapes for collapsed
        # patterns (e.g. hexagons for bubbles, hourglasses for frayed ropes),
        # but these should take up space that is a subset of the space taken up
        # by the rectangle, so just using a rectangle for layout should be ok.
        self.shape = "rectangle"

        name = f"{config.PT2HR_NOSPACE[self.pattern_type]}{self.unique_id}"
        # Use the Node constructor to initialize the rest of the stuff we need
        super().__init__(unique_id, name, {})

    def __repr__(self):
        return (
            f"{self.name} containing "
            f"nodes {self.get_node_ids()} from {self.start_node_ids} to "
            f"{self.end_node_ids}"
        )

    def _absorb_child_pattern(self, child_pattern):
        """Merges a child Pattern's contents into this Pattern.

        As of writing, this should only be applied if child_pattern is a chain
        (and this Pattern, i.e. "self," is a chain or cyclic chain).

        Note that this method has no conception of the AssemblyGraph in which
        these Patterns are contained: we leave it up to the caller to reroute
        edges.
        """
        # (This attr is set to False by default in the Node constructor)
        child_pattern.removed = True
        # Note that we should only need to go one level down -- this is because
        # the "absorption" process, if applicable, is done as soon as we create
        # a new Pattern. So we don't have to check e.g. the grandchildren, if
        # present, of this pattern. (I guess we could do this all at once at
        # the end of pattern detection, maybe? might be problematic tho.)
        for node in child_pattern.nodes:
            node.parent_id = self.unique_id
            self.nodes.append(node)
        for edge in child_pattern.edges:
            edge.parent_id = self.unique_id
            self.edges.append(edge)

        # there should never be a case where a node is both the start
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

    def make_into_split(self):
        raise WeirdError(f"Attempted to split Pattern {self}.")

    def get_descendant_info(self):
        """Returns descendant Node, Edge, and Pattern objs (and PatternStats).

        Note that we include this object in the returned list of Pattern
        objects, and in the returned PatternStats.

        Returns
        -------
        list of Nodes, list of Edges, list of Patterns, PatternStats
        """
        nodes = []
        edges = []
        patts = [self]
        patt_stats = PatternStats()
        patt_stats.update(self.pattern_type)
        for node in self.nodes:
            if is_pattern(node):
                pn, pe, pp, ps = node.get_descendant_info()
                nodes.extend(pn)
                edges.extend(pe)
                patts.extend(pp)
                patt_stats += ps
            else:
                nodes.append(node)
        for edge in self.edges:
            edges.append(edge)
        return nodes, edges, patts, patt_stats

    def to_dot(self, indent=config.INDENT):
        """Returns a DOT representation of this Pattern and its descendants.

        Parameters
        ----------
        indent: str
            "Outer indentation" to use in the DOT output. We'll increment the
            indentation for child nodes/edges/patterns of this pattern as well.

        Returns
        -------
        str
            DOT representation of this Pattern, in which the Pattern is
            represented as a "cluster" subgraph.
        """
        # inner indentation level
        ii = indent + config.INDENT
        gv = f"{indent}subgraph cluster_{self.name} {{\n"
        gv += f'{ii}style="filled";\n'
        gv += f'{ii}fillcolor="{config.PT2COLOR[self.pattern_type]}";\n'
        for obj_coll in (self.nodes, self.edges):
            for obj in obj_coll:
                gv += obj.to_dot(indent=ii)
        gv += f"{indent}}}\n"
        return gv

    def to_cyjs(self):
        # unlike to_dot(), we don't bother doing this recursively. we assume
        # the caller already knows about all nodes and edges in this pattern.
        # since this is called by a Component object that should be fine
        ele = {
            "data": {
                "id": str(self.unique_id),
                # as of writing this is redundant b/c name contains the ID,
                # and also probably we don't even want to label these. but
                # let's be careful for now
                "label": self.name,
            },
            "classes": config.PT2HR_NOSPACE[self.pattern_type],
        }
        if self.parent_id is not None:
            ele["data"]["parent"] = str(self.parent_id)
        return ele
