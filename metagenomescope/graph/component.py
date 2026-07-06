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

import networkx as nx
from .. import name_utils, ui_utils, config
from ..errors import WeirdError
from . import graph_utils
from .subgraph import Subgraph
from .decoupled_component import DecoupledComponent


class Component(Subgraph):
    """Represents a weakly connected component in an assembly graph."""

    def __init__(
        self,
        unique_id,
        nodes,
        edges,
        patterns,
        node_centric=True,
        length_field="length",
        record_node_names=True,
        count_positive_names=True,
    ):
        """Initializes this Component object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other Components) integer ID of this
            Component.

        nodes: list of Node

        edges: list of Edge

        patterns: list of Pattern

        node_centric: bool

        length_field: str

        record_node_names: bool

        count_positive_names: bool
        """
        # unique size rank index of this component (the cc in the graph with
        # the most nodes has size rank 1, the next biggest one has size rank 2,
        # etc). We store this to make searching through the graph easier.
        self.cc_num = None

        # Things to draw if using decoupling. Relevant for strand-tangled
        # components.
        self.decoupling_done = False
        self.dc_shown_node_ids = set()
        self.dc_shown_edge_ids = set()
        self.dc_inval_edge_ids = set()
        self.dc_shown_patt_ids = set()

        super().__init__(
            unique_id,
            f"TempComponentID{unique_id}",
            nodes,
            edges,
            patterns,
            node_centric=node_centric,
            length_field=length_field,
            record_node_names=record_node_names,
        )

    def set_cc_num(self, cc_num):
        """Updates the component number of this component and its children."""
        self.cc_num = cc_num
        self.name = f"cc{self.cc_num}_id{self.unique_id}"
        for obj in self.get_objs():
            obj.set_cc_num(cc_num)

    def decouple(self, g):
        """Tries to decouple this component.

        Parameters
        ----------
        g: nx.MultiDiGraph
            NetworkX representation of the full assembly graph (corresponding
            to the AssemblyGraph.graph object).

        Returns
        -------
        bool
            True if this component was decoupled, False if not.

        Notes
        -----
        - There is some ambiguity in how we determine which node orientations
          to fix. Like, as long as we consider all nodes in this component, any
          traversal approach "works" (i.e. we will end up showing all nodes
          once with a given orientation). Our goal is more specifically to
          minimize the amount of invalidated edges while maximizing the
          "linearity" of the resulting layout.

          We currently just use NetworkX's bfs_layers() function, which seems
          to work well for this, but maybe there are other methods that would
          be better (that explicitly "weight" outgoing edges more, in order to
          increase linearity).

          Consider a component like X -> Y -> ... -> -Y -> -X
                                    A -> B -> ... -> -B -> -A, where the ...s
          indicate these four paths kind of mixing together due to inverted
          repeats or something.

          In this graph, we want to ideally end up with XY...(-B)(-A) or
          AB...(-Y)(-X). Nothing is *wrong* if we end up with XY...BA or
          AB...YX or something -- since those are still valid decoupled
          representations of this component -- but they are not ideal, because
          they are not the most linear way of representing it. Probably there
          is a good way to formalize this that I am just missing out on.
        """
        if self.decoupling_done:
            raise WeirdError(f"{self} is already decoupled")
        if len(self.nodes) <= 1:
            raise WeirdError(f"{self} has <= 1 nodes")

        # maps orientationless node names (i.e. "X" for both X and -X) to a
        # fixed orientation
        on2orient = {}

        # Fix the highest-degree + node in this component as "shown"
        #
        # In a perfectly symmetric component, the highest degree node X
        # should also have a twin node -X with the same degree (right?)
        # Thus, we limit the max-degree node search here to + nodes.
        #
        # Also: we use is_fwd() instead of the node "orientation" data because
        # the DOT parsing code doesn't assign orientations even to LJA DOT
        # nodes, at least for now.
        fwd_nids = [
            n.unique_id for n in self.nodes if name_utils.is_fwd(n.basename)
        ]
        mid = graph_utils.get_max_degree_node(g, fwd_nids)
        m = self.nodeid2obj[mid]
        on2orient[name_utils.get_orientationless_name(m.basename)] = config.FWD

        # if we show a split node, we really should also show its
        # counterpart (I mean it's not like a huge deal if we omit the
        # counterpart but I think it would look gross and confusing).
        # USUALLY the max-degree node should not be split, but maybe it
        # could happen?
        #
        # A more elegant way of handling this would be only creating
        # fwd_nids to include unsplit nodes, but I fear some components
        # might ONLY include split nodes. Maybe? That should really not
        # happen but I'm too tired to prove it so let's be safe
        shown_nids = set()
        graph_utils.add_node_and_counterpart_ids(shown_nids, m)

        # Go through the graph and fix node orientations.
        # We use BFS to do this, which seems to work ok; see docstring.
        # Note that computing the induced subgraph and creating an
        # undirected graph view from it could be slow (but I doubt it
        # will be a bottleneck). If needed we can do BFS/etc manually
        ccug = nx.induced_subgraph(g, self.nodeid2obj.keys()).to_undirected(
            as_view=True
        )
        for nids in nx.bfs_layers(ccug, mid):
            for nid in nids:
                n = self.nodeid2obj[nid]
                on = name_utils.get_orientationless_name(n.basename)
                if on not in on2orient:
                    on2orient[on] = name_utils.get_orientation(n.basename)
                    graph_utils.add_node_and_counterpart_ids(shown_nids, n)

        # Was this component changed by fixing node orientations?
        # It might not have been, if it was not strand-tangled. (We
        # could encounter this case in FASTG / LJA DOT files, I guess.)
        if len(shown_nids) == len(self.nodes):
            # no, this component was not changed. move on.
            return False
        elif len(shown_nids) > len(self.nodes):
            # like, i know it should never happen. i just wanna be sure
            raise WeirdError(f"{self} caused the apocalypse what even")

        # Okay, we know this component was changed by fixing node
        # orientations, since |shown nodes| < |nodes|.

        # If (s, t) and (-t, -s) correspond to DIFFERENT amounts of
        # edges, then we can still do decoupling... but let's emit a
        # LOUD warning that drawing this component with decoupling may
        # not show some edges. (This should only happen with "explicit"
        # filetypes that have node orientations -- so, FASTG and LJA
        # DOT, I think. And even then this really shouldn't happen in
        # practice.)
        graph_utils.warn_if_cc_edge_cts_asymmetric(self)

        # Record what edges will be drawn in the decoupled version of
        # this component
        shown_eids = set()
        # ... and what edges are impossible to draw normally (even when
        # reverse-complemented) given just the shown nodes
        inval_edgetups = set()
        inval_eids = set()
        for e in self.edges:
            src_shown = e.new_src_id in shown_nids
            tgt_shown = e.new_tgt_id in shown_nids
            # If BOTH the source and target are shown, then we can draw
            # this edge! And if NEITHER the source and target is shown,
            # then we can draw its reverse complement. The tricky thing
            # is if exactly one of the source and target is shown.
            s = self.nodeid2obj[e.new_src_id].name
            t = self.nodeid2obj[e.new_tgt_id].name
            if src_shown and tgt_shown:
                shown_eids.add(e.unique_id)
            elif src_shown ^ tgt_shown:
                # If we reach this case, then exactly one of {source,
                # target} is shown, so this edge is invalidated.
                #
                # Consider the case where there are parallel
                # invalidated edges (multiple from s -> t and multiple
                # from -t -> -s). We could show (with the funky port
                # stuff) either all edges from s -> t, or all edges
                # from -t -> -s, but it would be confusing to show a
                # mix of edges. Thus, we arbitrarily say that we will
                # only show invalidated edges from one of the two
                # orientations (by storing the orientation as a tuple).
                if name_utils.negate_edge_tuple(s, t) not in inval_edgetups:
                    inval_edgetups.add((s, t))
                    inval_eids.add(e.unique_id)

        # Record this component, so that we can handle it specially
        # when drawing with the decoupling option turned on.
        self.dc_shown_node_ids = shown_nids
        self.dc_shown_edge_ids = shown_eids
        self.dc_inval_edge_ids = inval_eids
        self.dc_shown_patt_ids = graph_utils.get_avail_pattern_ids(
            self.patterns,
            self.dc_shown_node_ids,
            self.dc_shown_edge_ids,
        )
        self.decoupling_done = True
        return True

    def to_cyjs(
        self, scope_settings, modifier_settings, layout_alg, layout_params
    ):
        if self.decoupling_done and ui_utils.decouple(scope_settings):
            caller = DecoupledComponent(self)
        else:
            caller = super()
        return caller.to_cyjs(
            scope_settings, modifier_settings, layout_alg, layout_params
        )
