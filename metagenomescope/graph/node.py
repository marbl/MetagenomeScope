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


from metagenomescope import cy_config
from metagenomescope.config import SPLIT_SEP, SPLIT_LEFT, SPLIT_RIGHT, INDENT
from metagenomescope.errors import WeirdError, GraphParsingError


def get_node_name(basename, split):
    if split is None:
        return basename
    elif split == SPLIT_LEFT or split == SPLIT_RIGHT:
        return f"{basename}{SPLIT_SEP}{split}"
    else:
        raise WeirdError(
            f"split is {split}, but it should be one of "
            f"{{None, {SPLIT_LEFT}, {SPLIT_RIGHT}}}."
        )


def get_opposite_split(split):
    if split == SPLIT_LEFT:
        return SPLIT_RIGHT
    elif split == SPLIT_RIGHT:
        return SPLIT_LEFT
    else:
        raise WeirdError(
            f"split is {split}, but it should be {SPLIT_LEFT} or "
            f"{SPLIT_RIGHT}?"
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
            of None could, later on in the decomposition process, be split up
            (if this happens, it will be done when a counterpart Node of this
            node is added -- the counterpart Node's constructor will call
            .make_into_split() on this Node).

        counterpart_node: Node or None
            Node object that represents a "counterpart" Node from which we
            should copy this new Node's relative_length and longside_proportion
            attributes. We'll also call counterpart_node.make_into_split() to
            update it.

        Raises
        ------
        WeirdError
            - If split is not one of {None, SPLIT_LEFT, SPLIT_RIGHT}
            - If split is None and counterpart_node is not None, or vice versa
            - If counterpart_node already has a split that is not None
            - If counterpart_node already has another counterpart node
        """
        self.unique_id = unique_id
        self.basename = name
        self.name = get_node_name(self.basename, split)
        self.data = data
        self.split = split

        if counterpart_node is not None:
            if self.split is None:
                raise WeirdError(
                    f"Creating Node {self.unique_id}: counterpart_node is not "
                    "None, but split is None?"
                )
            # If the counterpart node already has split or counterpart_node_id
            # attrs defined, then its make_into_split() method will raise an
            # error
            counterpart_node.make_into_split(self.unique_id, self.split)
            self.counterpart_node_id = counterpart_node.unique_id
            self.relative_length = counterpart_node.relative_length
            self.longside_proportion = counterpart_node.longside_proportion
        else:
            if self.split is not None:
                raise WeirdError(
                    f"Creating Node {self.unique_id}: split is {self.split}, "
                    "but no counterpart Node specified?"
                )
            self.counterpart_node_id = None
            # Also will be filled in after node scaling. See
            # AssemblyGraph.scale_nodes().
            self.relative_length = None
            self.longside_proportion = None

        # Should be filled in with something later on to simplify random
        # coloring of nodes. See AssemblyGraph._init_graph_objs().
        self.rand_idx = None

        # We may fill this in with a reference to another Node object if we
        # notice another node that is the RC of this one. Note that this is
        # not guaranteed, since some filetypes (e.g. MetaCarvel GML) may not
        # describe two copies of each node.
        self.rc_node = None

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

        self._set_shape()

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        # This will be set later on, after we are finished with pattern
        # detection (and thus with splitting nodes, etc).
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

    def make_into_split(self, counterpart_id, counterpart_split_type):
        """Makes this Node into the split Node of a counterpart Node.

        Parameters
        ----------
        counterpart_id: int
            The unique ID of the counterpart Node.

        counterpart_split_type: str
            The split type of the counterpart Node. We'll set the split type of
            this Node to the opposite of this (so, if counterpart_split_type is
            SPLIT_LEFT, then this Node will have a split type of SPLIT_RIGHT).
        """
        if self.is_split():
            raise WeirdError(f"{self}: split attr is already {self.split}?")
        if self.counterpart_node_id is not None:
            raise WeirdError(
                f"{self}: counterpart_node_id attr is already "
                f"{self.counterpart_node_id}?"
            )
        self.counterpart_node_id = counterpart_id
        self.split = get_opposite_split(counterpart_split_type)
        self.name = get_node_name(self.basename, self.split)
        self._set_shape()

    def unsplit(self):
        if self.is_not_split():
            raise WeirdError(
                f"{self} can't be unsplit; it's already not split?"
            )
        self.split = None
        self.name = get_node_name(self.basename, self.split)

        if self.counterpart_node_id is None:
            raise WeirdError(
                f"{self} can't be unsplit; doesn't have a counterpart node ID?"
            )
        self.counterpart_node_id = None
        self._set_shape()

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

    def to_dot(self, indent=INDENT):
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
            f"{indent}{self.unique_id} [width={dotwidth},height={self.height},"
            f'shape={self.shape},label="{self.name}"];\n'
        )

    def to_cyjs(self, incl_patterns=True):
        if "orientation" in self.data:
            if self.data["orientation"] == "+":
                ndir = "fwd"
            else:
                ndir = "rev"
        else:
            ndir = "unoriented"

        splitcls = f"split{'N' if self.split is None else self.split}"

        ele = {
            "data": {
                # Cytoscape.js expects node IDs to be strings
                "id": str(self.unique_id),
                "label": self.name,
                # ensure that the callbacks for looking at selected node
                # data can distinguish btwn actual nodes and patterns. We may
                # be able to use this to replace some of the "classes" below
                # for styling (maybe some memory savings?) but probs nbd
                "ntype": cy_config.NODE_DATA_TYPE,
            },
            "classes": f"nonpattern {ndir} {splitcls} noderand{self.rand_idx}",
        }

        if incl_patterns and self.parent_id is not None:
            ele["data"]["parent"] = str(self.parent_id)

        return ele
