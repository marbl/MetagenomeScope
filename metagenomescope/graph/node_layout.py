import math
from metagenomescope import config
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
        if self.orientation == config.FWD:
            if self.split == config.SPLIT_LEFT:
                self.shape = "rect"
            elif self.split == config.SPLIT_RIGHT:
                self.shape = "invtriangle"
            else:
                self.shape = "invhouse"
        elif self.orientation == config.REV:
            if self.split == config.SPLIT_LEFT:
                self.shape = "triangle"
            elif self.split == config.SPLIT_RIGHT:
                self.shape = "rect"
            else:
                self.shape = "house"
        else:
            # NOTE: Graphviz doesn't support semicircles (as of writing). We
            # should be able to get around this by using custom shapes
            # (https://graphviz.org/faq/#FaqCustShape), but for now we just use
            # (inv)triangles as a hacky workaround.
            if self.split == config.SPLIT_LEFT:
                self.shape = "triangle"
            elif self.split == config.SPLIT_RIGHT:
                self.shape = "invtriangle"
            else:
                self.shape = "circle"

    def set_dims(self):
        if self.length is not None:
            m = max(math.log(self.length, 1000), 1)
            self.width = m * max(
                math.log(self.length, layout_config.NODE_SCALING_LOG_BASE), 1
            )
            self.height = self.width / 2.5
        else:
            # match flye's DOT files
            self.width = layout_config.NOLENGTH_NODE_WIDTH
            self.height = layout_config.NOLENGTH_NODE_HEIGHT

        # If a node is split, it's drawn with half its width. This way, the two
        # split nodes of an original node N have the same total area as N would
        # were it an un-split node, because hw = h*(w/2) + h*(w/2).
        if self.split is not None:
            self.width /= 2

    def get_dims(self, to_cyjs=True):
        if to_cyjs:
            return (
                self.width * layout_config.PIXELS_PER_INCH,
                self.height * layout_config.PIXELS_PER_INCH,
            )
        else:
            return self.width, self.height

    def to_dot(self, nodeid, nodelabel, indent=layout_config.INDENT):
        return layout_utils.get_node_dot(
            nodeid, nodelabel, self.width, self.height, self.shape, indent
        )
