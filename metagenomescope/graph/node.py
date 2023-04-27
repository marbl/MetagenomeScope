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
from metagenomescope.errors import WeirdError


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

    def __init__(self, unique_id, name, data, split=None):
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
        """
        self.unique_id = unique_id
        self.name = get_node_name(name, split)
        self.data = data
        self.split = split

        # Will be filled in after doing node scaling. Stored in points.
        self.width = None
        self.height = None

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

        # TODO: set this based on the data? Like, if the data has "orientation"
        # given, then set this to a house or invhouse; otherwise, set it to a
        # circle. and I guess update this if this node is split, also (taking
        # into account the previous shape).
        self.shape = "circle"

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        self.cc_num = None

    def __repr__(self):
        return f"Node {self.unique_id} (name: {self.name})"

    def set_scale_vals_from_other_node(self, other_node):
        self.relative_length = other_node.relative_length
        self.longside_proportion = other_node.longside_proportion

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
        self.name = get_node_name(self.name, self.split)

    def make_into_left_split(self):
        self._make_into_split(SPLIT_LEFT)

    def make_into_right_split(self):
        self._make_into_split(SPLIT_RIGHT)

    def set_cc_num(self, cc_num):
        self.cc_num = cc_num
