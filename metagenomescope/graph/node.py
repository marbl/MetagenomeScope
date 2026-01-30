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


from metagenomescope import cy_config, config, ui_utils
from metagenomescope.layout import layout_config
from metagenomescope.errors import WeirdError
from metagenomescope.graph import graph_utils
from .node_layout import NodeLayout


def get_node_name(basename, split):
    graph_utils.validate_split_type(split)
    if split is None:
        return basename
    elif split == config.SPLIT_LEFT:
        return f"{basename}{config.SPLIT_LEFT_SUFFIX}"
    else:
        # because we've already called validate_split_type(), we know
        # that the split type must be right if we have made it here
        return f"{basename}{config.SPLIT_RIGHT_SUFFIX}"


def get_opposite_split(split):
    if split == config.SPLIT_LEFT:
        return config.SPLIT_RIGHT
    elif split == config.SPLIT_RIGHT:
        return config.SPLIT_LEFT
    else:
        raise WeirdError(
            f"split is {split}, but it should be {config.SPLIT_LEFT} or "
            f"{config.SPLIT_RIGHT}?"
        )


class Node(object):
    """Represents a node in an assembly graph.

    Since the "type" of these assembly graphs is not strict (they can represent
    de Bruijn graphs, overlap graphs, ...), these nodes can have a lot of
    associated metadata (sequence information, coverage, ...), or barely any
    associated metadata.
    """

    def __init__(
        self,
        unique_id,
        name,
        data,
        split=None,
        counterpart_node=None,
        compound=False,
    ):
        """Initializes this Node object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes in the assembly graph)
            integer ID of this node.

        name: str
            Name of this node, to be displayed in the visualization interface.
            If split is not None, then the name of this node will be extended
            to "[node name][config.SPLIT_LEFT_SUFFIX]"
            or "[node name][config.SPLIT_RIGHT_SUFFIX]" -- for example, a left
            split node named "123" will be renamed to "123-L", if the
            config.SPLIT_* variables remain as their current defaults.

        data: dict
            Maps field names (e.g. "length", "orientation", "cov", ...) to
            their values for this node. The amount of this data will vary based
            on the input assembly graph's filetype (if no data is available for
            this node, this can be an empty dict).

        split: str or None
            If this is given, this should be either config.SPLIT_LEFT or
            config.SPLIT_RIGHT. config.SPLIT_LEFT indicates that this is a
            "left split" node, config.SPLIT_RIGHT indicates that this is a
            "right split" node, and None indicates that this is not a split
            node yet (I'm going to label these non- split nodes as "full," just
            for the sake of clarity -- see the Edge object docs for details).
            Note that a Node that has a split value of None could, later on in
            the decomposition process, be split up (if this happens, it will be
            done when a counterpart Node of this node is added -- the
            counterpart Node's constructor will call .make_into_split() on this
            Node).

        counterpart_node: Node or None
            Node object that represents a "counterpart" Node from which we
            should copy this new Node's relative_length and longside_proportion
            attributes. We'll also call counterpart_node.make_into_split() to
            update it.

        compound: bool
            If True, this node has children (i.e. it's a pattern). If False,
            it's just a normal node...

        Raises
        ------
        WeirdError
            - If split is not in {None, config.SPLIT_LEFT, config.SPLIT_RIGHT}
            - If split is None and counterpart_node is not None, or vice versa
            - If counterpart_node already has a split that is not None
            - If counterpart_node already has another counterpart node
        """
        self.unique_id = unique_id
        self.basename = name
        # this will take care of validating split
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
        else:
            if self.split is not None:
                raise WeirdError(
                    f"Creating Node {self.unique_id}: split is {self.split}, "
                    "but no counterpart Node specified?"
                )
            self.counterpart_node_id = None

        # Should be filled in with something later on to simplify random
        # coloring of nodes. See AssemblyGraph._init_graph_objs().
        self.rand_idx = None

        # We may fill this in with a reference to another Node object if we
        # notice another node that is the RC of this one. Note that this is
        # not guaranteed, since some filetypes (e.g. MetaCarvel GML) may not
        # describe two copies of each node.
        self.rc_node = None

        # ID of the pattern containing this node, or None if this node
        # exists in the top level of the graph.
        self.parent_id = None

        # Silly trick so that we don't have to write an is_pattern() function
        self.compound = compound

        # Number (1-indexed) of the connected component containing this node.
        # This will be set later on, after we are finished with pattern
        # detection (and thus with splitting nodes, etc).
        self.cc_num = None

        # Certain nodes may be "removed" from the graph -- for example, if we
        # perform splitting but then realize that splitting was not needed for
        # a node, then we'll merge its left and right split nodes back into a
        # single node. This flag is a simple way of tracking this.
        self.removed = False

        # will store info about shape, width/height, etc
        self.layout = NodeLayout(self.split, self.data)

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
            config.SPLIT_LEFT, then this Node will have a split type of
            config.SPLIT_RIGHT).
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
        self.layout.update_split(self.split)

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
        self.layout.update_split(self.split)

    def set_cc_num(self, cc_num):
        self.cc_num = cc_num

    def to_dot(self, indent=layout_config.INDENT):
        return self.layout.to_dot(self.unique_id, self.name, indent)

    def to_cyjs(self, draw_settings):
        if "orientation" in self.data:
            if self.data["orientation"] == config.FWD:
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

        ele["data"]["w"], ele["data"]["h"] = self.layout.get_dims(pixels=True)

        if (
            ui_utils.show_patterns(draw_settings)
            and self.parent_id is not None
        ):
            ele["data"]["parent"] = str(self.parent_id)

        return ele
