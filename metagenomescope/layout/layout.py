import pygraphviz
from . import layout_utils, layout_config
from .. import ui_utils, config
from ..errors import WeirdError


class Layout(object):
    """Performs layout on some part of the graph and outputs the results.

    This could reflect the layout of a single pattern, an entire component,
    a subregion of the graph, etc.
    """

    def __init__(self, region, draw_settings):
        """Initializes this Layout object.

        Parameters
        ----------
        region: Subgraph or Pattern

        draw_settings: list
        """
        self.region = region
        self.draw_settings = draw_settings
        self.incl_patterns = ui_utils.show_patterns(draw_settings)
        self.recursive = ui_utils.do_recursive_layout(draw_settings)

        # I know this is a jank way of testing if this is a pattern or a
        # Subgraph but i don't want to cause circular imports by importing
        # those types in to check that so.... whatever, sure, let's use hasattr
        # See https://stackoverflow.com/q/39740632 for some discussion about
        # this issue (which IS A REAL ISSUE i'm not going crazy)
        # (ok i might be going crazy but that's about other things)
        self.region_is_pattern = hasattr(self.region, "pattern_type")

        # when laid out as a "solid object," this region will be represented
        # as just a rectangle. ofc in the fancy viz we may use a diff shape
        self.shape = "rectangle"

        # these attributes will be set in _run(), after we've laid out all
        # the stuff inside this region
        self.dot = None
        self.width = None
        self.height = None
        self.nodeid2rel = {}
        self.edgeid2rel = {}
        self.pattid2rel = {}
        self.regionid2dims = {}

        self._run()

    def __repr__(self):
        return f"Layout({self.region}; {self.draw_settings})"

    def at_top_level_of_region(self, obj):
        # if the region is a pattern then check if obj parent id matches the
        # region; otherwise, check if obj parent id is None (i.e. if the obj
        # has no parent and is thus at the top level of the graph)
        if self.region_is_pattern:
            return obj.parent_id == self.region.unique_id
        else:
            return obj.parent_id is None

    def _to_dot(self):
        """Creates a DOT string describing the top level of this region.

        This will lay out descendant patterns as needed recursively,
        assuming that self.incl_patterns and self.recursive are True.
        """
        dot = ""
        dot += layout_utils.get_gv_header(self.region.name)
        if self.incl_patterns and self.recursive:
            for node in self.region.nodes:
                if self.at_top_level_of_region(node):
                    if node.compound:
                        # "node" is a collapsed pattern; lay it out first
                        lay = Layout(node, self.draw_settings)
                        dot += lay.to_solid_dot()
                        self.nodeid2rel.update(lay.nodeid2rel)
                        self.edgeid2rel.update(lay.edgeid2rel)
                        self.pattid2rel.update(lay.pattid2rel)
                        self.regionid2dims.update(lay.regionid2dims)
                    else:
                        # "node" is just a normal node. just an innocent node.
                        # https://www.youtube.com/watch?v=lr_vl62JblQ
                        dot += node.to_dot()

            for edge in self.region.edges:
                if self.at_top_level_of_region(edge):
                    dot += edge.to_dot(level="dec")

            # If this region is a subgraph/component, then it stores patterns
            # separately from nodes. as above, lay out patterns recursively.
            #
            # TODO: it would be nice to not have to make this distinction --
            # so, making patterns store nodes and patterns separately i guess,
            # like Subgraphs do. But then we'd need to update a bunch of
            # decomposition stuff, eep!
            if not self.region_is_pattern:
                for pattern in self.region.patterns:
                    if self.at_top_level_of_region(pattern):
                        lay = Layout(pattern, self.draw_settings)
                        dot += lay.to_solid_dot()
                        self.nodeid2rel.update(lay.nodeid2rel)
                        self.edgeid2rel.update(lay.edgeid2rel)
                        self.pattid2rel.update(lay.pattid2rel)
                        self.regionid2dims.update(lay.regionid2dims)
        else:
            if self.region_is_pattern:
                raise WeirdError(f"Yeah this doesn't make sense chief {self}")

            if self.incl_patterns and not self.recursive:
                for pattern in self.region.patterns:
                    if self.at_top_level_of_region(pattern):
                        dot += layout_utils.get_pattern_cluster_dot(pattern)
                for node in self.region.nodes:
                    if self.at_top_level_of_region(node):
                        dot += node.to_dot()
                for edge in self.region.edges:
                    if self.at_top_level_of_region(edge):
                        dot += edge.to_dot(level="new")

            else:
                for node in self.region.nodes:
                    dot += node.to_dot()
                for edge in self.region.edges:
                    dot += edge.to_dot()
        dot += "}"
        return dot

    def to_solid_dot(self, indent=layout_config.INDENT):
        """Creates a DOT string describing the bounding box of this layout.

        For example, this is what takes care of like laying out a pattern
        as just a solid rectangular node.
        """
        color = None
        if self.region_is_pattern:
            color = config.PT2COLOR[self.region.pattern_type]
        return layout_utils.get_node_dot(
            self.region.unique_id,
            self.region.name,
            self.width,
            self.height,
            self.shape,
            indent,
            color,
        )

    def _save_rel_coords(self, cg):
        """Saves relative coordinates after the recursive pattern layout.

        This should only be used if self.incl_patterns and self.recursive
        are both True.
        """
        # Extract relative node coordinates (x and y) -- for child nodes
        # and patterns. (As with ._to_dot() above, remember that Subgraphs
        # don't store patterns in .nodes -- they store them in .patterns.
        # So we'll do another pass later on to catch child patterns if this
        # region is a Subgraph, not a Pattern.)
        #
        # NOTE: Because this checks if the unique ID is in self.nodeid2rel,
        # this will only consider top-level children of this pattern. Stuff
        # located on deeper layers of the hierarchy should already be in
        # self.nodeid2rel.
        for node in self.region.nodes:
            if node.unique_id not in self.nodeid2rel:
                pgv_node = cg.get_node(node.unique_id)
                if node.compound:
                    d = self.pattid2rel
                else:
                    d = self.nodeid2rel
                d[node.unique_id] = layout_utils.getxy(pgv_node.attr["pos"])

        # Extract (relative) edge control points
        for edge in self.region.edges:
            if edge.unique_id not in self.edgeid2rel:
                # If this is a parallel edge, then get_edge() should give us an
                # arbitrary one of these edges. At the end of this block, we
                # call cg.remove_edge() to ensure that the next time -- if any
                # -- that we call cg.get_edge() with these node IDs, we get a
                # different edge position.
                #
                # THAT BEING SAID if these are parallel edges proobs they don't
                # need to be laid out with fancy control pt stuff
                src, tgt = edge.dec_src_id, edge.dec_tgt_id
                pgv_edge = cg.get_edge(src, tgt)
                self.edgeid2rel[edge.unique_id] = (
                    layout_utils.get_control_points(pgv_edge.attr["pos"])
                )
                cg.remove_edge(pgv_edge)

        # If this is a Subgraph/Component, extract top-level child pattern
        # relative coordinates
        if not self.region_is_pattern:
            for pattern in self.region.patterns:
                if pattern.unique_id not in self.pattid2rel:
                    pgv_patt = cg.get_node(pattern.unique_id)
                    self.pattid2rel[pattern.unique_id] = layout_utils.getxy(
                        pgv_patt.attr["pos"]
                    )
        self.regionid2dims[self.region.unique_id] = (self.width, self.height)

    def _run(self):
        """Lays out this region."""

        # Actually do layout
        self.dot = self._to_dot()
        with open("scrap/layouts/" + self.region.name + ".gv", "w") as f:
            f.write(self.dot)
        cg = pygraphviz.AGraph(self.dot)
        cg.layout(prog="dot")

        # Extract dimension info. The first two coordinates in the bounding box
        # (bb) should always be (0, 0).
        # The width and height we store here are large enough in order to
        # contain the layout of the stuff we just laid out.
        self.width, self.height = layout_utils.get_bb_x2_y2(
            cg.graph_attr["bb"]
        )

        if self.incl_patterns and self.recursive:
            self._save_rel_coords(cg)
        else:
            for node in self.region.nodes:
                pgv_node = cg.get_node(node.unique_id)
                self.nodeid2rel[node.unique_id] = layout_utils.getxy(
                    pgv_node.attr["pos"]
                )

            for edge in self.region.edges:
                src, tgt = edge.new_src_id, edge.new_tgt_id
                pgv_edge = cg.get_edge(src, tgt)
                self.edgeid2rel[edge.unique_id] = (
                    layout_utils.get_control_points(pgv_edge.attr["pos"])
                )
                # account for parallel edges -- see _save_rel_coords() comment
                cg.remove_edge(pgv_edge)

    def to_abs_coords(self):
        """Returns the absolute coordinates of descendant nodes and edges.

        Basically, if you did the default thing of using patterns + doing
        recursive layout, then this will go through and convert coordinates
        to be absolute (instead of relative to whatever parent pattern a
        node/edge has).

        And if you did something else, then we don't really need to *convert*
        anything, but we still return the results in the same format to make
        life easier for the caller. yay!

        Returns
        -------
        nodeid2xy, edgeid2ctrlpts:
                dict of int -> (int, int), dict of int -> list of int

            Exactly what they say on the tin.

        Raises
        ------
        WeirdError
            If self.region is not a Subgraph/Component/etc. It doesn't make
            sense to call this if the region for this layout is just a pattern.
            (I mean we COULD support that but why)

        Notes
        -----
        - More work needs to be done to convert edge ctrl pts to Cytoscape.js
          format. layout_utils.shift_control_points() is a start, but then you
          still have to do the conversion to the sort of format Cy.js expects;
          see convertCtrlPtsToDistsAndWeights() in the old drawer.js code.

        - In Graphviz coordinates, the origin is at the bottom left corner
          (https://graphviz.org/docs/outputs/);
          in Cytoscape.js coordinates, the origin is at the top left corner
          (https://js.cytoscape.org/#notation/position).
          Thus, this function flips y-coordinates so that the stuff drawn in
          Cytoscape.js matches Graphviz.
        """
        if self.region_is_pattern:
            raise WeirdError(
                "Why are you calling to_abs_coords() on a Pattern's layout? "
                f"{self}"
            )
        nodeid2xy = {}
        edgeid2ctrlpts = {}
        # pattid2bb = {}
        if self.incl_patterns and self.recursive:
            for node in self.region.nodes:
                if node.compound:
                    # self.region.nodes should only contain patterns if
                    # self.region IS a pattern, and that should never happen
                    raise WeirdError(f"no!!!! {self} {node}")
                # TODO: remember to flip the y coords!
                nodeid2xy[node.unique_id] = self.nodeid2rel[node.unique_id]
            for edge in self.region.edges:
                edgeid2ctrlpts[edge.unique_id] = self.edgeid2rel[
                    edge.unique_id
                ]
        else:
            for node in self.region.nodes:
                x, y = self.nodeid2rel[node.unique_id]
                y = self.height - y
                nodeid2xy[node.unique_id] = x, y
            for edge in self.region.edges:
                edgeid2ctrlpts[edge.unique_id] = self.edgeid2rel[
                    edge.unique_id
                ]
        return nodeid2xy, edgeid2ctrlpts
