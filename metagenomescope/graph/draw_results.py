from .. import ui_utils
from ..errors import WeirdError
from ..layout import layout_config
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
        # i worry about jank side effects from modifying this class. so, safety
        # first
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

        eles = []
        widths = [lay.width for lay in self.region2layout.values()]
        row_width = sum(widths) / layout_config.BB_ROW_WIDTH_FRAC
        print("hi here!", widths, row_width)

        curr_row_width = 0
        curr_row_height = 0
        x = 0
        y = 0
        curr_row_max_height = 0
        for r in self.get_sorted_regions():
            lay = self.region2layout[r]
            nodeid2xy, edgeid2ctrlpts = lay.to_abs_coords()

            for n in r.nodes:
                j = n.to_cyjs(self.draw_settings)
                nx, ny = nodeid2xy[n.unique_id]
                print(n, nx, ny, x, y)
                j["position"] = {"x": nx + x, "y": ny + y}
                eles.append(j)

            for e in r.edges:
                j = e.to_cyjs(self.draw_settings)
                # TODO implement
                # if e.unique_id in edgeid2ctrlpts:
                #     straight, cpd, cpw = edgeid2ctrlpts[e.unique_id]
                #     if not straight:
                #         j["classes"] += " withctrlpts"
                #         j["data"]["cpd"] = cpd
                #         j["data"]["cpw"] = cpw
                eles.append(j)

            if self.incl_patterns:
                eles.extend(p.to_cyjs() for p in r.patterns)

            x += lay.width
            curr_row_max_height = max(curr_row_max_height, lay.height)
            if x >= row_width:
                x = 0
                y += curr_row_max_height + layout_config.BB_YPAD
            else:
                x += layout_config.BB_XPAD
        return eles
