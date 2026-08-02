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


from metagenomescope import config
from metagenomescope.layout import layout_config, layout_utils
from metagenomescope.errors import WeirdError
from .edge import Edge


class InvalidatedEdge(Edge):
    r"""Represents an invalidated edge in a decoupled subgraph.

    Notes
    -----
    Okay so like what does that mean? When we perform decoupling, we fix each
    node's shown orientation to be either + or -, and figure out which edges
    to show based on that.

    So, let's say that we have a strand-tangled graph that looks like

       A         -B
       /--> (Y) --\
    (X)            (-X)
       \--> (-Y) -/
       B          -A

    Nodes are X, Y, -X, -Y; edges are A, B, -A, -B.

    Let's say we fix shown node orientations X = +, Y = -. This means that
    we know we can show edge B, since both of its adjacent nodes are shown;
    and we know we can't show edge -B, since neither of its adjacent nodes
    are shown.

    But what about edges A and -A? We can't show A (from X -> Y), since Y is
    not shown; and we can't show -A (from -Y -> -X), since -X is not shown.

    We say that edges A and -A are *invalidated* -- fixing node orientations
    prevents these edges (and their reverse-complementary edges, aka each
    other) from being visible in the decoupled graph.

    The way around this is picking either A or -A, and drawing it in a way
    that connects the one node of it that is shown and the opposite port of
    the RC of its unshown node. So, if we pick A, then we know that X is
    shown but Y isn't. Thus, draw the edge from X to the opposite port of -Y
    to indicate that the edge is from X -> Y.

    Anyway, as you would imagine, it is kind of annoying to reason about edges
    from one node to another node where one of these nodes is not drawn! Hence
    this class, which should make life a bit easier.
    """

    def __init__(self, e, inval_type, rc_node_id):
        """Initializes this InvalidatedEdge object based on a normal Edge.

        Parameters
        ----------
        e: Edge
            Original edge in the graph that can't be shown in a decoupled
            subgraph, because either its source or target node (but not both!)
            is unshown. This InvalidatedEdge object will represent this edge.

        inval_type: str
            One of {config.INVAL_SRC, config.INVAL_TGT}. INVAL_SRC indicates
            that the source node of this edge is unshown (but its target node
            is shown); INVAL_TGT indicates that the target node of this edge is
            unshown (but its source node is shown).

        rc_node_id: int
            We will draw this edge as being between its shown node and the
            reverse-complement of its unshown node (adjusting the port on the
            RC unshown node). This is the ID of that RC node.

        Notes
        -----
        To explain this a bit: in the above example, if we were to pick edge A,
        we would create an InvalidatedEdge object based on the X -> Y edge.
        Since X is shown but Y is not, this edge would have an inval_type of
        INVAL_TGT. The RC node would be -Y, indicating that we should draw the
        edge from X to the opposite port of -Y.
        """
        if e.is_fake:
            raise WeirdError(f"Trying to invalidate a fake edge {e}?")

        # since InvalidatedEdges won't be drawn as children of patterns, and
        # since we're already done with the decomposition, the only "level" of
        # node information we care about (see Edge docstring) is the rerouted
        # source/target ID, aka the new_*_id stuff.
        src_id = e.new_src_id
        tgt_id = e.new_tgt_id
        if inval_type == config.INVAL_SRC:
            src_id = rc_node_id
            self.ports = ("w", "w")
        elif inval_type == config.INVAL_TGT:
            tgt_id = rc_node_id
            self.ports = ("e", "e")
        else:
            raise WeirdError(f"Unrecognized inval_type: {inval_type}")

        self.e = e
        self.inval_type = inval_type
        self.rc_node_id = rc_node_id
        super().__init__(e.unique_id, src_id, tgt_id, e.data)

        # just to be consistent, make these match the underlying edge's attrs.
        # Eventually it might be nice to add a special Edge() constructor that
        # takes an existing Edge as input (a la
        # https://stackoverflow.com/a/2164383) so we don't have to worry about
        # managing these attributes here, in this other code file, but whatevs.
        self.rand_idx = e.rand_idx
        self.parent_id = e.parent_id
        self.set_cc_num(e.cc_num)

    def __repr__(self):
        return "Inval" + super().__repr__()

    def to_dot(self, level="new", is_back=False, indent=layout_config.INDENT):
        if level != "new":
            raise WeirdError(f"Only level='new' supported: inval edge {self}")

        return layout_utils.get_edge_dot(
            self.new_src_id,
            self.new_tgt_id,
            self.unique_id,
            # yeah, i know self.is_fake should always be False, but let's be
            # paranoid and future-proof this. Can we pretend that fake edges in
            # the night skies are like shooting stars?
            is_fake=self.is_fake,
            is_back=is_back,
            is_inval=True,
            ports=self.ports,
            indent=indent,
        )

    def to_cyjs(self, scope_settings):
        ele = super().to_cyjs(scope_settings)
        ele["classes"] += " inval"
        if self.inval_type == config.INVAL_SRC:
            ele["classes"] += " invalsrc"
        else:
            ele["classes"] += " invaltgt"
        return ele
