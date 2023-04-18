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


def get_node_name(basename, split):
    if split is None:
        return basename
    elif split == "L" or split == "R":
        return f"{basename}-{split}"
    else:
        raise WeirdError(
            f'"split" is {split}, but it should be one of '
            '{None, "L", "R"}.'
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
            to "[node name]-[split]" -- for example, a node named "123" with a
            split value of "L" will be named "123-L" in the visualization
            interface, to make it easier to search for this node vs. "123-R".

        data: dict
            Maps field names (e.g. "length", "orientation", "depth", ...) to
            their values for this node. The amount of this data will vary based
            on the input assembly graph's filetype (if no data is available for
            this node, this can be an empty dict).

        split: str or None
            If this is given, this should be either "L" or "R". "L" indicates
            that this is a "left split" node, "R" indicates that this is a
            "right split" node, and None indicates that this is not a split
            node (I'm going to label these non-split nodes as "full," just for
            the sake of clarity -- see the Edge object docs for details).
            Note that a Node that has a split value of None could, later
            on in the decomposition process, be split up. Such a change should
            be reflected in two new Nodes being created (rather than the
            original Node being modified), although that sort of behavior is up
            to the AssemblyGraph code.
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

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Number (1-indexed) of the connected component containing this node.
        self.cc_num = None

    def __repr__(self):
        return f"Node {self.unique_id}"
