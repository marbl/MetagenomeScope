import pygraphviz
from . import layout_utils, layout_config


class Layout(object):
    """Performs layout on some part of the graph and outputs the results.

    This could reflect the layout of a single pattern, an entire component,
    a subregion of the graph, etc.
    """

    def __init__(self, region, incl_patterns=True):
        """Initializes this Layout object.

        Parameters
        ----------
        region: Subgraph or Pattern

        incl_patterns: bool
            If True, include patterns in the layout (and do the whole thing
            of laying out the graph recursively). If False, ignore patterns,
            and just act like their descendant nodes/edges have no parents.
        """
        self.region = region
        self.incl_patterns = incl_patterns

        # I know this is a jank way of testing if this is a pattern or a
        # Subgraph but i don't want to cause circular imports by importing
        # those types in to check that so.... whatever, sure, let's use hasattr
        # See https://stackoverflow.com/q/39740632 for some discussion about
        # this issue (which IS A REAL ISSUE i'm not going crazy)
        # (ok i might be going crazy but that's about other things)
        self.region_is_pattern = hasattr(self.region, "compound")

        # when laid out as a "solid object," this region will be represented
        # as just a rectangle. ofc in the fancy viz we may use a diff shape
        self.shape = "rectangle"

        # these attributes will be set in _run(), after we've laid out all
        # the stuff inside this region
        self.nodeid2rel = {}
        self.edgeid2rel = {}
        self.width = None
        self.height = None

        self._run()

    def _run(self):
        """Lays out this region."""
        # If incl_patterns=True, calling .to_dot() will recursively lay out
        # patterns contained within these regions
        dot = self.to_dot()

        cg = pygraphviz.AGraph(dot)
        cg.layout(prog="dot")

        # Extract dimension info. The first two coordinates in the bounding box
        # (bb) should always be (0, 0).
        # The width and height we store here are large enough in order to
        # contain the layout of the stuff we just laid out.
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
        for node in self.region.nodes:
            if node.unique_id not in self.nodeid2rel:
                cn = cg.get_node(node.unique_id)
                self.nodeid2rel[node.unique_id] = layout_utils.getxy(
                    cn.attr["pos"]
                )

        # Extract (relative) edge control points
        for edge in self.region.edges:
            if edge.unique_id not in self.edgeid2rel:
                # If this is a parallel edge between dec_src_id and dec_tgt_id,
                # then get_edge() should give us an arbitrary one of these edges.
                # At the end of this block, we call cg.remove_edge() to ensure
                # that the next time -- if any -- that we call cg.get_edge() with
                # these node IDs, we get a different edge position.
                #
                # THAT BEING SAID if these are parallel edges proobs they don't
                # need to be laid out with fancy control pt stuff
                ce = cg.get_edge(edge.dec_src_id, edge.dec_tgt_id)
                self.edgeid2rel[edge.unique_id] = (
                    layout_utils.get_control_points(ce.attr["pos"])
                )
                cg.remove_edge(ce)

    def at_top_level_of_region(self, obj):
        # if the region is a pattern then check if obj parent id matches the
        # region; otherwise, check if obj parent id is None (i.e. if the obj
        # has no parent and is thus at the top level of the graph)
        if self.region_is_pattern:
            return obj.parent_id == self.region.unique_id
        else:
            return obj.parent_id is None

    def to_dot(self, incl_bounds=True):
        """Creates a DOT string describing the top-level of these regions."""
        dot = ""
        if incl_bounds:
            dot += layout_utils.get_gv_header()
        if self.incl_patterns:
            # top level nodes and edges, relative to this region
            for node in self.region.nodes:
                if self.at_top_level_of_region(node):
                    if node.compound:
                        lay = Layout(node)
                        dot += lay.to_solid_dot()
                        self.nodeid2rel.update(lay.nodeid2rel)
                        self.edgeid2rel.update(lay.edgeid2rel)
                    else:
                        dot += node.to_dot()

            for edge in self.region.edges:
                if self.at_top_level_of_region(edge):
                    dot += edge.to_dot(level="dec")

            # Lay out bottommost patterns first
            # Pattern objects don't have a .patterns attr; they just store
            # children that are collapsed patterns in .nodes. However,
            # Subgraphs and Components do have .patterns
            if hasattr(self.region, "patterns"):
                for pattern in self.region.patterns:
                    if self.at_top_level_of_region(pattern):
                        lay = Layout(pattern)
                        dot += lay.to_solid_dot()
                        self.nodeid2rel.update(lay.nodeid2rel)
                        self.edgeid2rel.update(lay.edgeid2rel)

        else:
            for node in self.region.nodes:
                dot += node.to_dot()
            for edge in self.region.edges:
                dot += edge.to_dot()
        if incl_bounds:
            dot += "}"
        return dot

    def to_solid_dot(self, indent=layout_config.INDENT):
        """Creates a DOT string describing the bounding box of this layout.

        For example, this is what takes care of like laying out a pattern
        as just a solid rectangular node.
        """
        return layout_utils.get_node_dot(
            self.region.unique_id,
            self.region.name,
            self.width,
            self.height,
            self.shape,
            indent,
        )

    def to_cyjs(self):
        with open(f"scrap/layouts/{self.region.unique_id}.gv", "w") as f:
            f.write(self.to_dot())

        # TODO extract cyjs from nodes/edges (using self.nodeid2rel
        # and self.edgeid2rel) and add in positions from layout
