import math
from collections import defaultdict
from .. import ui_utils
from ..layout import layout_utils
from ..errors import WeirdError
from . import graph_utils


class DrawResults(object):
    """Takes care of preparing Cytoscape.js JSON elements to be drawn."""

    def __init__(self, region2layout, scope_settings, modifier_settings):
        """Initializes this DrawResults object.

        Parameters
        ----------
        region2layout: dict of Subgraph -> (Layout or None)
            Can be {}. I guess that's useful if you want to define an instance
            of this to which you'll later add other DrawResults objects.

        scope_settings: list
            Describes what to draw (e.g. should we draw patterns?)

        modifier_settings: list
            Describes settings for how we should draw things. Most of these
            should already have been considered during layout, but some are
            relevant here -- e.g. horizontally centering rows impacts the
            component tiling procedure.

        Notes
        -----
        The region2layout thing exploits the fact that Subgraphs are hashable.
        """
        self.region2layout = region2layout
        self.scope_settings = scope_settings
        self.modifier_settings = modifier_settings
        self.incl_patterns = ui_utils.show_patterns(self.scope_settings)
        self.hcenter = ui_utils.hcenter(self.modifier_settings)

        # if we see even a single layout that is None, we will immediately give
        # up on processing layouts. In practice we should never see mix-and-
        # match things where only some regions have a layout so this is fine
        self.layouts_given = True
        self.num_full_nodes = 0
        self.num_real_edges = 0
        self.num_patterns = 0
        for r, lay in self.region2layout.items():
            self.num_full_nodes += r.num_full_nodes
            self.num_real_edges += r.num_real_edges
            if self.incl_patterns:
                self.num_patterns += len(r.patterns)
            if lay is None:
                self.layouts_given = False

    def get_fancy_count_text(self):
        nsum = ui_utils.pluralize(self.num_full_nodes, "node")
        esum = ui_utils.pluralize(self.num_real_edges, "edge")
        psum = ui_utils.pluralize(self.num_patterns, "pattern")
        return f"{nsum}, {esum}, {psum}"

    def __repr__(self):
        asum = self.get_fancy_count_text()
        rsum = ui_utils.pluralize(len(self.region2layout), "region")
        return (
            f"DrawResults({rsum} ({asum}); {self.scope_settings}; "
            f"{self.modifier_settings})"
        )

    def get_node_and_edge_ids(self):
        nodeids = []
        edgeids = []
        for r in self.region2layout:
            for n in r.nodes:
                nodeids.append(n.unique_id)
            for e in r.edges:
                edgeids.append(e.unique_id)
        return nodeids, edgeids

    def __add__(self, other):
        """Adds two DrawResults objects and does some validation.

        We can add two DrawResults objects together if they have:

        1. identical scope settings (e.g. "show patterns").
        2. identical modifier settings (e.g. "horizontally center rows").
        3. no overlapping regions (i.e. no subgraphs represented by both
           DrawResults objects for some reason).

        You could probably make an argument for relaxing any of these criteria,
        but these should always hold in practice (... as of writing) so whatevs
        """
        if self.scope_settings != other.scope_settings:
            raise WeirdError(f"Incompatible scope settings: {self}, {other}")

        if self.modifier_settings != other.modifier_settings:
            raise WeirdError(
                f"Incompatible modifier settings: {self}, {other}"
            )

        if set(self.region2layout) & set(other.region2layout):
            raise WeirdError(
                "Regions present in multiple DrawResults: "
                f"{self.region2layout}, {other.region2layout}"
            )

        # we could MAYBE do self.region2layout.update(other.region2layout) but
        # i worry about jank side effects from modifying self in __add__(). so,
        # safety first
        d = self.region2layout.copy()
        for r, lay in other.region2layout.items():
            d[r] = lay
        return DrawResults(d, self.scope_settings, self.modifier_settings)

    def get_sorted_regions(self):
        """Sorts all of the regions represented here.

        As of writing, self.region2layout should contain either:

        - ONLY Components or Subgraphs representing decoupled components, or
        - JUST a single non-Component Subgraph

        It shouldn't contain both non-Component Subgraphs and Components, etc.
        But just to future-proof this, we allow that.

        This returns regions in the following order:

        1. All Subgraphs that have a cc_num attribute, sorted by cc_num (lower
           cc nums, i.e. bigger components, go first).

        2. All other Subgraphs, sorted using graph_utils.get_sorted_subgraphs()
           (so, using the same criteria as how we assigned cc nums -- bigger
           subgraphs first)
        """
        ccs = []
        non_ccs = []
        for r in self.region2layout:
            if hasattr(r, "cc_num"):
                ccs.append(r)
            else:
                non_ccs.append(r)

        sorted_ccs = sorted(ccs, key=lambda c: c.cc_num)
        sorted_non_ccs = graph_utils.get_sorted_subgraphs(non_ccs)
        return sorted_ccs + sorted_non_ccs

    def get_nolayout_eles(self):
        eles = []
        for r in self.region2layout:
            eles.extend(n.to_cyjs(self.scope_settings) for n in r.nodes)
            eles.extend(e.to_cyjs(self.scope_settings) for e in r.edges)
            if self.incl_patterns:
                eles.extend(p.to_cyjs() for p in r.patterns)
        return eles

    def pack(self):
        """Packs layouts as needed; returns Cytoscape.js JSON for all elements.

        Returns
        -------
        eles: list of dict
            Each entry describes a node / edge / pattern in the graph. This
            list can be plopped directly into a Cytoscape.js object's
            "elements" field.

        References
        ----------
        This is essentially me trying to imitate how Bandage packs the
        components of graphs. Their codebase includes a much more elegant
        implementation of this: https://github.com/rrwick/Bandage/blob/f94d409a76bf6a13eef6af0a88476eaeffa71b32/ogdf/energybased/MAARPacking.cpp#L60
        """
        if not self.layouts_given:
            return self.get_nolayout_eles()

        # TODO should turn these into user-configurable params
        min_xpad = 50
        min_ypad = 200
        xpadfrac = 0.15
        max_num_regions_before_breakpoint = 3
        # roughly 10 / 16 - a bit taller than a standard 16:9 aspect ratio, since
        # we are accounting for the control panel. Not 100% sure how good this
        # will look on tiny screens.
        # ideally we'd actually get this from the JS/HTML when we run layout...
        goal_hwr = 1 / 1.6

        sorted_regions = self.get_sorted_regions()

        areas = []
        for r in sorted_regions:
            lay = self.region2layout[r]
            areas.append(lay.width * lay.height)

        # PASS 0: DETERMINE THE WIDTH OF EACH ROW
        # There are currently a few different ways of doing this:
        #
        # 1. We find a reasonable "breakpoint" where the size of a region R_N
        #    is much bigger than the size of the next-up region R_{N+1}. Define
        #    R_N and all the regions to the left of it (i.e. the earlier things
        #    in sorted_regions) as the first row. (Note that we require R_N to
        #    have at least a couple of nodes. This prevents junk like 2-node
        #    chain ccs from being "breakpoints" as compared to 1-node ccs.)
        #
        #    This idea of looking at relative region dimensions is inspired by
        #    Bandage -- I ended up using area instead of width (seems to adapt
        #    to semilinear/hierarchical layouts better?? idk).
        #
        # 2. If we are not able to find a reasonable breakpoint, then we
        #    set the row width as something proportional to the sqrt of the
        #    total areas of the regions. this seems to work ok?
        #
        # 3. If there is just a single region then ofc that's the row width
        row_width = None
        if len(sorted_regions) > 1:
            i = 0
            tentative_first_row_width = 0
            while (
                i < len(sorted_regions) - 1
                and i < max_num_regions_before_breakpoint
            ):
                r = sorted_regions[i]
                # the notion of breakpoints doesn't make sense when
                # we are dealing with 1-node ccs
                if len(r.nodes) == 1:
                    break
                lay = self.region2layout[r]
                tentative_first_row_width += lay.width
                # If this is not the first component in this row, make sure to
                # add on padding from the component to the left of it. DON'T
                # ADD ON PADDING for the current component until we know that
                # it is not the final one in this row; otherwise, the row width
                # we set will be too large, so subsequent rows will extend past
                # the first row and that will look slightly gross :(((((
                #
                # Test case: Velvet E. coli graph, draw all components using
                # sfdp and patterns - before I fixed this, later rows would be
                # longer than the first one because I added in padding for that
                # first component! oh no!!! it's all good now though :)
                if i > 0:
                    prev_lay = self.region2layout[sorted_regions[i - 1]]
                    tentative_first_row_width += layout_utils.get_xpad(
                        prev_lay, min_xpad, xpadfrac
                    )
                # Detect breakpoints. Inspired by Bandage:
                # https://github.com/rrwick/Bandage/blob/f94d409a76bf6a13eef6af0a88476eaeffa71b32/ogdf/energybased/MAARPacking.cpp#L107
                if areas[i] / areas[i + 1] > 10 and len(r.nodes) > 5:
                    # Set the current (i-th) region as the last one in the
                    # first row
                    row_width = tentative_first_row_width
                    break
                i += 1
            if row_width is None:
                # No breakpoints found, so set row width automatically. Use of
                # sqrt() inspired by https://www.graphviz.org/pdf/gvpack.1.pdf
                row_width = math.sqrt(sum(areas)) * 3.5
        else:
            row_width = self.region2layout[sorted_regions[0]].width

        # PASS 1: COMPUTE REGION ROWS AND X-POSITIONS
        # Now that we have the row width set, figure out which row each
        # region should go in -- and which x-coordinate each region should
        # have within these rows.
        x = 0
        curr_row = 0
        r2xrow = {}
        row2max_height = defaultdict(int)
        row2max_width = defaultdict(int)
        for r in sorted_regions:
            lay = self.region2layout[r]

            end_row_after_adding_this_region = False
            # don't include padding to the RIGHT of this region in
            # the computation of if it can fit in this row. Because if
            # the region fits, but the padding to the right of it doesn't,
            # then that doesn't matter because we won't draw anything to
            # the right of it in this row anyway.
            so_far_width = x + lay.width
            if so_far_width >= row_width:
                # This region's layout either hits or goes past row_width,
                # so we need to move to a new row.
                if x > 0 and so_far_width > row_width:
                    # There is already other stuff to the left of us on the
                    # current row AND this region's layout goes past the end of
                    # the row. (We check that, using so_far_width > row_width,
                    # in order to account for "breakpoint" row width cases
                    # where e.g. the second and third ccs have a breakpoint
                    # btwn them. Test case for this: Verkko v1.1 hg002 graph.)
                    #
                    # Anyway, end this row now; we'll add this region as the
                    # first thing on the next row.
                    curr_row += 1
                    x = 0
                else:
                    # There is nothing to the left of us on the current
                    # row. This means that the width of this region alone
                    # is >= row_width! Wow.
                    #
                    # Let's expand row_width for all rows below this one,
                    # so that this doesn't stick out awkwardly.
                    # (might change this in the future...)
                    row_width = so_far_width
                    end_row_after_adding_this_region = True

            r2xrow[r] = (x, curr_row)

            row2max_height[curr_row] = max(
                row2max_height[curr_row], lay.height
            )
            # only increase a row's max width when we add a region to it;
            # avoids rightmost padding in a row counting towards row width
            row2max_width[curr_row] = max(
                row2max_width[curr_row], x + lay.width
            )

            x += lay.width + layout_utils.get_xpad(lay, min_xpad, xpadfrac)

            if end_row_after_adding_this_region:
                curr_row += 1
                x = 0

        # PASS 2: ADJUST MINIMUM Y-PADDING
        # We *could* not bother with this and just set the y-padding to some
        # constant, but that can result in drawings with weird aspect ratios.

        # total height of all rows, without adding any y-padding at all
        h = sum(row2max_height.values())
        num_rows = len(row2max_height)
        if num_rows > 1:
            # height-to-width ratio, if we didn't use any y-padding at all
            min_hwr = h / row_width

            if min_hwr < goal_hwr:
                # Case 1: the current height-to-width ratio < the goal ratio.
                # Expand the minimum y-padding (after each row) as needed, to
                # try to fit the goal ratio. Kiiinda like what Bandage does.
                #
                # If we add y-padding of some fixed number P, then this would
                # occur in each of the spaces between rows -- and there are
                # |rows| - 1 such spaces (just like how your hand [probably]
                # has 5 fingers, and 5 - 1 = 4 spaces between fingers).
                #
                # Thus, if we want to figure out the y-padding needed to
                # stretch out the display to make the height-width ratio
                # equal to T, we can set (H + (P * (|rows| - 1))) / W = T.
                # (Where H = total height without y-padding, W = row width, and
                # T = goal ratio of height-to-width.)
                #
                # Solving for P gives us P = (TW - H) / (|rows| - 1). Note that
                # P is positive when H / W < T, which should always be the case
                # if the above if statement was True.
                ratio_ypad = ((goal_hwr * row_width) - h) / (num_rows - 1)
                # Allow the minimum y-padding to expand to ratio_ypad, which
                # will get us to the desired height-to-width ratio (ignoring
                # any y-padding adjustments that might happen in pass 3 below).
                #
                # We set an upper bound on how big this can be, and say that
                # the min y-padding must be <= some fraction of the total row
                # height without padding (h). This addresses the case where
                # there are just a few not-very-tall rows (otherwise you just
                # see two-row drawings have one at the top and one at the
                # bottom with a bunch of dead space between).
                min_ypad = min(max(min_ypad, ratio_ypad), h / 2)

            # Case 2: the height-to-width ratio >= the goal ratio, and we
            # skipped the above block entirely (and left min_ypad as whatever
            # its default numeric value is).
            #
            # This can happen if the drawing includes just ... a LOT of stuff,
            # or if there are some really tall components. Test case: the
            # hg002-verkko1.1.gfa file -- drawing all ccs with only nr ccs +
            # decoupling triggers this, as of writing -- the H:W ratio before
            # y-padding is 0.878 ._.
            #
            # Anyway, in this case we STILL NEED TO ADD SOME Y-PADDING because
            # otherwise the graph will (probably) look cluttered. We'll do this
            # in pass 3 below.

        # PASS 3: COMPUTE ROW Y-POSITIONS, ADJUSTING PADDING IF NEEDED
        # We may have set min_ypad above, in which case we cooould just use
        # that for all of the y-paddings here. But we allow the amount of
        # y-padding after a row to be adjusted.
        y = 0
        row2y = {}
        for row in range(num_rows):
            row2y[row] = y
            row_height = row2max_height[row]
            # If we didn't set min_ypad (or even if we did and it's just kind
            # of small), then allow for row heights to expand y-padding after.
            relative_row_height = row_height / h
            # I used Wolfram Alpha to fit a curve to these points, which works
            # and everything, but it's easier to reason about this - and more
            # efficient, right? - to just hardcode some thresholds.
            # (For reference, the curve is 10.0132x^2 - 7.50184x + 1.31615.)
            if relative_row_height <= 0.01:
                f = 1.5
            if relative_row_height <= 0.02:
                f = 1
            elif relative_row_height <= 0.1:
                f = 0.5
            elif relative_row_height <= 0.2:
                f = 0.2
            elif relative_row_height <= 0.3:
                f = 0.1
            else:
                f = 0.03
            y += row_height + max(min_ypad, f * row_height)

        # PASS 4: HORIZONTALLY CENTER ROWS, IF REQUESTED
        # (Unlike vertical centering, which I guess we need to do for each
        # region, horizontally centering each row can just be done once up top)
        row2xoffset = {}
        if self.hcenter:
            for row in range(num_rows):
                row2xoffset[row] = (row_width - row2max_width[row]) / 2

        # PASS 5: ACTUALLY ASSIGN POSITIONS TO ELEMENTS
        # All rows (and, thus, regions)' positions are fixed by this point,
        # so this part is straightforward.
        eles = []
        for r in sorted_regions:
            lay = self.region2layout[r]
            x, row = r2xrow[r]
            # horizontally center stuff within the row, if requested
            if self.hcenter:
                x += row2xoffset[row]
            # vertically center stuff within the row
            y = row2y[row] + ((row2max_height[row] - lay.height) / 2)
            nodeid2xy, edgeid2ctrlpts = lay.to_abs_coords(x, y)

            for n in r.nodes:
                j = n.to_cyjs(self.scope_settings)
                nx, ny = nodeid2xy[n.unique_id]
                j["position"] = {"x": nx, "y": ny}
                eles.append(j)

            for e in r.edges:
                j = e.to_cyjs(self.scope_settings)
                layout_utils.try_add_control_points_to_cyjs(
                    j, e, edgeid2ctrlpts
                )
                eles.append(j)

            if self.incl_patterns:
                eles.extend(p.to_cyjs() for p in r.patterns)

        return eles
