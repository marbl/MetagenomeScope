import math
from .. import ui_utils
from ..errors import WeirdError
from . import graph_utils


class DrawResults(object):
    """Takes care of preparing Cytoscape.js JSON elements to be drawn."""

    def __init__(self, region2layout, draw_settings):
        """Initializes this DrawResults object.

        Parameters
        ----------
        region2layout: dict of Subgraph -> (Layout or None)
            Can be {}. I guess that's useful if you want to define an instance
            of this to which you'll later add other DrawResults objects.

        draw_settings: list

        Notes
        -----
        The region2layout thing exploits the fact that Subgraphs are hashable.
        """
        self.region2layout = region2layout
        self.draw_settings = draw_settings
        self.incl_patterns = ui_utils.show_patterns(self.draw_settings)

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
        return f"DrawResults({rsum} ({asum}); {self.draw_settings})"

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
        """Adds two DrawResults objects and does some validation."""
        if self.draw_settings != other.draw_settings:
            raise WeirdError(f"Incompatible draw settings: {self}, {other}")

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
        return DrawResults(d, self.draw_settings)

    def get_sorted_regions(self):
        """Sorts all of the regions represented here.

        As of writing, self.region2layout should either contain ONLY Components
        or just a single non-Component Subgraph. It shouldn't contain both. But
        just to future-proof this, we allow for both.

        This returns regions in the following order:

        1. All Components, sorted by cc_num (lower cc nums, i.e. bigger
           components, go first)

        2. All non-Components, sorted using graph_utils.get_sorted_subgraphs()
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
            eles.extend(n.to_cyjs(self.draw_settings) for n in r.nodes)
            eles.extend(e.to_cyjs(self.draw_settings) for e in r.edges)
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
        """
        if not self.layouts_given:
            return self.get_nolayout_eles()

        # TODO should turn these into user-configurable params
        min_xpad = 100
        min_ypad = 100
        xpadfrac = 0.1
        ypadfrac = 0.1

        areas = []
        widths = []
        for lay in self.region2layout.values():
            widths.append(lay.width)
            areas.append(lay.width * lay.height)

        sorted_regions = self.get_sorted_regions()
        # pass 0: determine the width of each row.
        # There are currently three ways of doing this:
        #
        # 1. We find a reasonable "breakpoint" where the width of a region R_N
        #    is > 2x the width of the next-up region R_{N+1}. We define R_N
        #    and all the regions to the left of it (i.e. the bigger regions,
        #    going by sorted_regions) as the first row.
        #
        # 2. If we are not able to find a reasonable break point, then we
        #    set the row width as something proportional to the sqrt of the
        #    total areas of the regions. this seems to work ok?
        #
        # 3. If there is just a single region then obviously that's the row
        #    width
        row_width = None
        if len(sorted_regions) > 1:
            i = 0
            tentative_first_row_width = 0
            while i < len(sorted_regions) - 1 and i < 5:
                r = sorted_regions[i]
                # the notion of breakpoints doesn't make sense when
                # we are dealing with 1-node ccs
                if len(r.nodes) == 1:
                    break
                lay = self.region2layout[r]
                next_lay = self.region2layout[sorted_regions[i + 1]]
                tentative_first_row_width += lay.width + max(
                    min_xpad, xpadfrac * lay.width
                )
                # inspired by bandage:
                # https://github.com/rrwick/Bandage/blob/f94d409a76bf6a13eef6af0a88476eaeffa71b32/ogdf/energybased/MAARPacking.cpp#L107
                wratio = lay.width / next_lay.width
                if wratio > 2:
                    # choose this point to cut off the first row
                    row_width = tentative_first_row_width
                    break
                i += 1
            if row_width is None:
                # sqrt() inspired by https://www.graphviz.org/pdf/gvpack.1.pdf
                row_width = math.sqrt(sum(areas)) * 3.5
        else:
            row_width = widths[0]

        x = 0
        y = 0
        curr_row = 0
        curr_row_max_height = 0
        r2xrow = {}
        row2y = {curr_row: 0}
        row2max_height = {}
        # pass 1: compute region positions and row heights
        for r in sorted_regions:
            lay = self.region2layout[r]
            cell_width = lay.width + max(min_xpad, xpadfrac * lay.width)
            # don't include padding to the RIGHT of this region in
            # the computation of if it can fit in this row. Because if
            # the region fits, but the padding to the right of it doesn't,
            # then that doesn't matter because we won't draw anything to
            # the right of it in this row anyway.
            if x > 0 and x + lay.width > row_width:
                if x == 0:
                    row_width = x + cell_width
                row2max_height[curr_row] = curr_row_max_height
                y += curr_row_max_height + max(
                    min_ypad, ypadfrac * curr_row_max_height
                )
                curr_row += 1
                row2y[curr_row] = y
                x = 0
                curr_row_max_height = 0

            r2xrow[r] = (x, curr_row)
            x += cell_width
            curr_row_max_height = max(curr_row_max_height, lay.height)

        if curr_row not in row2max_height:
            row2max_height[curr_row] = curr_row_max_height

        # pass 2: actually assign positions to elements
        eles = []
        for r in sorted_regions:
            lay = self.region2layout[r]
            x, row = r2xrow[r]
            # vertically center stuff within the row
            y = row2y[row] + ((row2max_height[row] - lay.height) / 2)
            nodeid2xy, edgeid2ctrlpts = lay.to_abs_coords(x, y)

            for n in r.nodes:
                j = n.to_cyjs(self.draw_settings)
                nx, ny = nodeid2xy[n.unique_id]
                j["position"] = {"x": nx, "y": ny}
                eles.append(j)

            for e in r.edges:
                j = e.to_cyjs(self.draw_settings)
                if e.unique_id in edgeid2ctrlpts:
                    straight, cpd, cpw = edgeid2ctrlpts[e.unique_id]
                    if not straight:
                        j["classes"] += " withctrlpts"
                        j["data"]["cpd"] = cpd
                        j["data"]["cpw"] = cpw
                eles.append(j)

            if self.incl_patterns:
                eles.extend(p.to_cyjs() for p in r.patterns)

        return eles
