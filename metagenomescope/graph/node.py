# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.


from metagenomescope.config import SPLIT_SEP, SPLIT_LEFT, SPLIT_RIGHT
from metagenomescope.errors import WeirdError, GraphParsingError


def get_node_name(basename, split):
    if split is None:
        return basename
    elif split == SPLIT_LEFT or split == SPLIT_RIGHT:
        return f"{basename}{SPLIT_SEP}{split}"
    else:
        raise WeirdError(
            f'"split" is {split}, but it should be one of '
            f'{{None, "{SPLIT_LEFT}", "{SPLIT_RIGHT}"}}.'
        )


class Node(object):
    """Represents a node in an assembly graph.

    Since the "type" of these assembly graphs is not strict (they can represent
    de Bruijn graphs, overlap graphs, ...), these nodes can have a lot of
    associated metadata (sequence information, coverage, ...), or barely any
    associated metadata.
    """

    def __init__(
        self, unique_id, name, data, split=None, counterpart_node=None
    ):
        """Initializes this Node object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes in the assembly graph)
            integer ID of this node.

        name: str
            Name of this node, to be displayed in the visualization interface.
            (If split is not None, then the name of this node will be extended
            to "[node name][SPLIT_SEP][split]" -- for example, a left split
            node named "123" will be renamed to "123-L", if SPLIT_SEP and
            SPLIT_LEFT remain their current defaults.)

        data: dict
            Maps field names (e.g. "length", "orientation", "depth", ...) to
            their values for this node. The amount of this data will vary based
            on the input assembly graph's filetype (if no data is available for
            this node, this can be an empty dict).

        split: str or None
            If this is given, this should be either SPLIT_LEFT or SPLIT_RIGHT.
            SPLIT_LEFT indicates that this is a "left split" node, SPLIT_RIGHT
            indicates that this is a "right split" node, and None indicates
            that this is not a split node yet (I'm going to label these non-
            split nodes as "full," just for the sake of clarity -- see the Edge
            object docs for details). Note that a Node that has a split value
            of None could, later on in the decomposition process, be split up.
            You should do this by calling the .make_into_left_split() /
            .make_into_right_split() functions on this Node.

        counterpart_node: Node or None
            Node object that represents a "counterpart" Node from which we
            should copy this new Node's relative_length and longside_proportion
            attributes. We'll also set the counterpart_node_id attribute
            of this new Node to the ID of the counterpart Node, and set
            counterpart_node.counterpart_node_id to this new Node's ID. (This
            will be useful later when we detect/remove "unnecessary" split
            nodes.) If split is None or if counterpart_node.counterpart_node_id
            is not None, then we'll raise an error.
        """
        self.unique_id = unique_id
        self.basename = name
        self.name = get_node_name(self.basename, split)
        self.data = data
        self.split = split

        # Will be filled in after doing node scaling. Stored in points.
        self.width = None
        self.height = None

        if counterpart_node is not None:
            if self.split is None:
                raise WeirdError(
                    f"Node {self.unique_id}: counterpart_node is not None, but "
                    "split is None?"
                )
            if counterpart_node.counterpart_node_id is None:
                counterpart_node.counterpart_node_id = self.unique_id
            else:
                raise WeirdError(
                    f"Creating split Node {self.unique_id}: {counterpart_node} "
                    "already has counterpart "
                    f"{counterpart_node.counterpart_node_id}?"
                )
            self.counterpart_node_id = counterpart_node.unique_id
            self.relative_length = counterpart_node.relative_length
            self.longside_proportion = counterpart_node.longside_proportion
        else:
            self.counterpart_node_id = None
            # Also will be filled in after node scaling. See
            # AssemblyGraph.scale_nodes().
            self.relative_length = None
            self.longside_proportion = None

        # Relative position of this node within its parent pattern, if this
        # node is located within a pattern. (None if this node exists in the
        # top level of the graph.) Stored in points.
        self.relative_x = None
        self.relative_y = None

        # Absolute position of this node within its connected component.
        self.x = None
        self.y = None

        self._set_shape()

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        self.cc_num = None

        # Certain nodes may be "removed" from the graph -- for example, if we
        # perform splitting but then realize that splitting was not needed for
        # a node, then we'll merge its left and right split nodes back into a
        # single node. This flag is a simple way of tracking this.
        self.removed = False

    def __repr__(self):
        return f"Node {self.unique_id} (name: {self.name})"

    def is_split(self):
        return self.split is not None

    def is_not_split(self):
        return not self.is_split()

    def _make_into_split(self, split_type):
        if self.is_split():
            raise WeirdError(
                f"This Node's .split attr is already {self.split}?"
            )
        self.split = split_type
        self.name = get_node_name(self.basename, self.split)
        self._set_shape()

    def unsplit(self):
        if self.is_not_split():
            raise WeirdError("Can't unsplit an already-not-split Node?")
        self.split = None
        self.name = get_node_name(self.basename, self.split)

        if self.counterpart_node_id is None:
            raise WeirdError(
                f"Shouldn't {self} already have a counterpart node ID?"
            )
        self.counterpart_node_id = None
        self._set_shape()

    def make_into_left_split(self):
        self._make_into_split(SPLIT_LEFT)

    def make_into_right_split(self):
        self._make_into_split(SPLIT_RIGHT)

    def set_cc_num(self, cc_num):
        self.cc_num = cc_num

    def _set_shape(self):
        if self.split not in (SPLIT_LEFT, SPLIT_RIGHT, None):
            raise WeirdError(f"Unrecognized split value: {self.split}")

        if "orientation" in self.data:
            orientation = self.data["orientation"]
            # If a node has a weird messed-up orientation, we can also just
            # make it a circle shape or something -- but it's safer to loudly
            # throw an error, esp since i don't think this should normally
            # happen
            if orientation not in ("+", "-"):
                raise GraphParsingError(
                    f"Unsupported node orientation: {orientation}. Should be "
                    '"+" or "-". If this is not the result of an error '
                    "somewhere and is actually a real orientation in your "
                    "graph, please open an issue on GitHub so we can add "
                    "support for it!"
                )

            if orientation == "+":
                if self.split == SPLIT_LEFT:
                    self.shape = "rect"
                elif self.split == SPLIT_RIGHT:
                    self.shape = "invtriangle"
                else:
                    self.shape = "invhouse"
            else:
                if self.split == SPLIT_LEFT:
                    self.shape = "triangle"
                elif self.split == SPLIT_RIGHT:
                    self.shape = "rect"
                else:
                    self.shape = "house"
        else:
            # NOTE: Graphviz doesn't support semicircles (as of writing). We
            # should be able to get around this by using custom shapes
            # (https://graphviz.org/faq/#FaqCustShape), but for now we just use
            # (inv)triangles as a hacky workaround.
            if self.split == SPLIT_LEFT:
                self.shape = "triangle"
            elif self.split == SPLIT_RIGHT:
                self.shape = "invtriangle"
            else:
                self.shape = "circle"

    def to_dot(self, label=True):
        if label:
            labelstr = f',label="{repr(self)}",fixedsize=true'
        else:
            labelstr = ""

        if self.split is not None:
            hgt = self.height / 2
        else:
            hgt = self.height
        return (
            f"\t{self.unique_id} [height={hgt},width={self.width},"
            f"shape={self.shape}{labelstr}];\n"
        )
