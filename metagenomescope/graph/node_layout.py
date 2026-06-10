import math
from metagenomescope import config
from metagenomescope.errors import WeirdError
from metagenomescope.layout import layout_config, layout_utils


class NodeLayout(object):
    """Stores information about a node's dimensions and shape."""

    def __init__(self, split, data):
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
        if self.orientation == config.FWD:
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
            # NOTE: Graphviz doesn't support semicircles (as of writing)
            # but whatever rects are fine
            self.shape = "rect"

    def set_dims(self):
        if self.length is not None:

            # What should the ratio of width:height be?
            #
            # Adjust based on order of magnitude, to make longer sequences
            # appear "longer" in the drawing.
            r = min(max(math.log(self.length, 100), 1), 6)

            # I played around a lot with the various options here -- see eg
            # https://www.wolframalpha.com/input?i=log10%28x%29+and+log100%28x%29+and+log10%28x%29%5E2+and+log100%28x%29%5E2+from+x+%3D+1+to+x%3D++5+million
            # ... this seems to offer a good mix of "long sequences look big
            # but not too big" and "small sequences are not too small." IDK.
            # I'm sure there are better ways to do this.
            area = max(math.log(self.length, 10), 1) ** 2

            # A = wh, and w = rh.
            # We thus know that A = (rh) * h = rh^2.
            # From there we can solve for A / r = h^2, and then sqrt(A/r) = h.
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

    def get_dims(self, units=layout_config.UNIT_GV_POINTS):
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
