from metagenomescope import config
from metagenomescope.errors import WeirdError


class NodeLayout(object):
    def __init__(self, split, data):
        # this can change! see update_split()
        self.split = split

        if "orientation" in data:
            self.orientation = data["orientation"]
        else:
            self.orientation = None

        # Will be filled in after doing node scaling. Stored in points.
        self.width = None
        self.height = None

        # Relative position of this node within its parent pattern, if this
        # node is located within a pattern. (None if this node exists in the
        # top level of the graph.) Stored in points.
        self.relative_x = None
        self.relative_y = None

        # Absolute position of this node within its connected component.
        self.x = None
        self.y = None

        self.set_shape()

    def update_split(self, new_split):
        self.split = new_split
        self.set_shape()

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

    def to_dot(self, nodeid, nodelabel, indent=config.INDENT):
        if self.width is None or self.height is None:
            raise WeirdError(
                "Can't call to_dot() on a Node with unset width and/or height"
            )
        # If a node is split, it's drawn with half its width. This way, the two
        # split nodes of an original node N have the same total area as N would
        # were it an un-split node, because hw = h*(w/2) + h*(w/2).
        if self.split is not None:
            dotwidth = self.width / 2
        else:
            dotwidth = self.width
        return (
            f"{indent}{nodeid} [width={dotwidth},height={self.height},"
            f'shape={self.shape},label="{nodelabel}"];\n'
        )
