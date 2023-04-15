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


from metagenomescope.errors import WeirdError

class Node(object):
    """Represents a node in an assembly graph.

    Since the "type" of these assembly graphs is not strict (they can represent
    de Bruijn graphs, overlap graphs, ...), these nodes can have a lot of
    associated metadata (sequence information, coverage, ...), or barely any
    any associated metadata.
    """
    def __init__(
        self,
        unique_id,
        orientation=None,
        relative_length=None,
        longside_proportion=None,
        split=None,
    ):
        """Initializes this node object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes in the assembly graph)
            integer ID of this node.

        orientation: str or None
            If this is given, it should be either "+" or "-". This can be None
            if nodes in the input graph don't have orientations.

        relative_length: float or None
            If this is given, it should be in the inclusive range [0, 1]. This
            can be None if nodes in the input graph don't have lengths.

        longside_proportion: float or None
            If this is given, it should be in the inclusive range [0, 1]. This
            can be None if nodes in the input graph don't have lengths.

        split: str or None
            If this is given, this should be either "L" or "R". "L" indicates
            that this is a "left split" node, "R" indicates that this is a
            "right split" node, and None indicates that this is not a split
            node.
        """
        self.unique_id = unique_id
        self.orientation = orientation
        self.relative_length = relative_length
        self.longside_proportion = longside_proportion
        self.split = split

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

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        self.cc_num = None

        # Extra data fields from the input -- can be located in the assembly
        # graph file (e.g. GC content, if this node corresponds to a sequence
        # and we have access to this sequence), and eventually should be
        # generalized to other metadata files
        # (https://github.com/marbl/MetagenomeScope/issues/243).
        self.extra_data = {}

    def __repr__(self):
        return f"Node {self.unique_id}"

    def add_extra_data(self, key, value):
        if key in self.extra_data:
            raise WeirdError(
                f"Key {key} is already present in the extra data for node "
                f"{self.unique_id}?"
            )
        self.extra_data[key] = value
