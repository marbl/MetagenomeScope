import pygraphviz
from .. import misc_utils
from . import layout_utils


class Layout(object):
    """Performs layout on some part of the graph and outputs the results.

    This could reflect the layout of a single pattern, an entire component,
    a subregion of the graph, etc.

    TODO: define some mechanism for adding Layouts? for component tiling.
    """

    def __init__(
        self,
        components=[],
        nodes=[],
        edges=[],
        patterns=[],
        incl_patterns=True,
    ):
        """Initializes this Layout object."""
        misc_utils.verify_at_least_one_nonempty(
            components, nodes, edges, patterns
        )
        self.components = components
        self.nodes = nodes
        self.edges = edges
        self.patterns = patterns
        self.incl_patterns = incl_patterns
        self.run()

    def run(self):
        pass

    def layout_pattern(self):
        gv_input = layout_utils.get_gv_header()
        # Recursively go through all of the nodes within this pattern. If any
        # of these isn't actually a node (and is actually a pattern), then lay
        # out that pattern!
        for node in self.nodes:
            if True:  # type(node) is Pattern:
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
            # TODO 2: okay well actually, if these are parallel edges, we can
            # PROBABLY safely fall back to just basic beziers unless these are
            # back edges....
            cg_edge = cg.get_edge(edge.dec_src_id, edge.dec_tgt_id)
            edge.relative_ctrl_pt_coords = layout_utils.get_control_points(
                cg_edge.attr["pos"]
            )
