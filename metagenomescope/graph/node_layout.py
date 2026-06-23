import math
from metagenomescope import config, cy_config
from metagenomescope.errors import WeirdError
from metagenomescope.layout import layout_config, layout_utils


class NodeLayout(object):
    """Stores information about a node's dimensions and shape."""

    def __init__(self, split, data, is_isolated_circle=False):
        # this can change! see update_split()
        self.split = split

        if "orientation" in data:
            self.orientation = data["orientation"]
        else:
            self.orientation = None

        if "length" in data:
            self.length = data["length"]
        else:
            self.length = None

        self.is_isolated_circle = is_isolated_circle

        self.set_shape()
        self.set_dims()

    def update_split(self, new_split):
        self.split = new_split
        self.set_shape()
        self.set_dims()

    def set_shape(self):
        # sets the shape used for layout in graphviz
        # these don't need to perfectly match up with the cy.js shapes. it's
        # safest if they are actually LARGER than the cy.js shapes right? or
        # like if they at least take up the same dimensions but more area.
        if self.is_isolated_circle:
            # ignore orientation
            self.shape = "circle"
        elif self.orientation == config.FWD:
            if self.split == config.SPLIT_LEFT:
                self.shape = "rect"
            elif self.split == config.SPLIT_RIGHT:
                # we could use triangles but those have smaller dimensions
                self.shape = "rect"
            else:
                self.shape = "invhouse"
        elif self.orientation == config.REV:
            if self.split == config.SPLIT_LEFT:
                # we could use triangles but those have smaller dimensions
                self.shape = "rect"
            elif self.split == config.SPLIT_RIGHT:
                self.shape = "rect"
            else:
                self.shape = "house"
        else:
            # the node has no orientation (so presumably the input graph is a
            # LJA / Flye edge-centric DOT file). Draw it as a circle or semi-
            # circle. Graphviz doesn't support semicircles (as of writing), but
            # whatever; just reserve a rectangular area and fill it in in cy.js
            self.shape = "rect"

    def set_dims(self):
        if self.length is not None:
            # Played around a lot with the various options here...
            # I'm sure there are better ways to do this.
            area = min(max(math.sqrt(self.length) / 10, 0.5), 3000)

            # Alternative approach: set area as linearly proportional to seq
            # length. This actually works surprisingly well for some graphs
            # (e.g. individual aug1 components, or all of the hifiasm-meta
            # ATCC graph) -- it does a good job of highlighting differences.
            #
            # However, when a graph has both very tiny and very large nodes,
            # the small nodes can seem to be almost invisible. Plus edge
            # thicknesses and font sizes are way too tiny. I think this
            # approach could be good if we change around some things (e.g.
            # autoscaling edge thicknesses/etc, stricter clamping based on
            # the range of sizes in the graph).
            ### area = min(max(self.length / 100, 1), 10_000_000)

            if self.is_isolated_circle:
                # area of a circle = pi * radius^2
                # flipped around, radius = sqrt(area / pi). we are setting
                # the diameter of the circle here, which is 2 * the radius.
                radius = math.sqrt(area / math.pi)
                self.width = self.height = 2 * radius

            else:
                # What should the ratio of width:height be?
                #
                # Adjust based on order of magnitude, to make longer sequences
                # appear "longer" in the drawing.
                # log100(x) = 1 occurs when x <= 100.
                # log100(x) = 6 occurs when x >= 1e12 (aka 1 trillion).
                r = min(max(math.log(self.length, 100), 1), 6)

                # Because the area of a pentagon is only a fraction of the
                # area of its rectangular bounding box, we multiply the area
                # of the bounding box by 1 over this fraction to scale up the
                # area of the pentagon to match. See cy_config.py for details.
                area *= cy_config.ONE_OVER_P_AREA_FRAC

                # A = wh, and w = rh.
                # We thus know that A = (rh) * h = rh^2.
                # From there we can solve for A / r = h^2 --> sqrt(A/r) = h.
                self.height = math.sqrt(area / r)
                self.width = self.height * r
        else:
            # mimic flye's DOT files
            self.width = layout_config.NOLENGTH_NODE_WIDTH
            self.height = layout_config.NOLENGTH_NODE_HEIGHT

        # fwd/rev split nodes have shapes that fit squarely within the (-1, 1)
        # bounding box that cytoscape.js accepts for shape-polygon-points. so,
        # we can safely just scale those split nodes' shapes by 1/2 to allocate
        # half the width to them.
        #
        # semicircles -- i.e. split unoriented nodes -- are different, since
        # representing a semicircle in a way that fills a grid is kind of jank
        # i think. so the cy.js shape takes up half the shape-polygon-points
        # bounding box, meaning that we DON'T decrease the allocated width
        # since it has already been "penalized" by getting a shape with half
        # the width.
        if self.split is not None and self.orientation is not None:
            self.width /= 2

    def get_dims(self, units):
        if units == layout_config.UNIT_GV_POINTS:
            sf = layout_config.POINTS_PER_INCH
        elif units == layout_config.UNIT_CY_PIXELS:
            sf = layout_config.PIXELS_PER_INCH
        elif units == layout_config.UNIT_GV_INCHES:
            sf = 1
        else:
            raise WeirdError(f'Unrecognized unit: "{units}"')

        return self.width * sf, self.height * sf

    def to_dot(self, nodeid, nodelabel, indent=layout_config.INDENT):
        return layout_utils.get_node_dot(
            nodeid, nodelabel, self.width, self.height, self.shape, indent
        )
