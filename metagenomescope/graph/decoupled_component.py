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

from .. import config
from ..layout import layout_utils
from ..errors import WeirdError
from . import graph_utils
from .subgraph import Subgraph


class DecoupledComponent(Subgraph):
    """Represents a decoupled connected component."""

    def __init__(self, cc):
        """Initializes this object.

        Parameters
        ----------
        cc: Component
        """
        if not cc.decoupling_done:
            raise WeirdError(f"{cc} not decoupled?")

        # Set the component number attribute so this is sorted properly
        # by DrawResults.get_sorted_regions()
        self.cc_num = cc.cc_num

        # "Invalidated edges" are edges from s -> t where one of (s, t) is not
        # present in the set of "shown nodes," but its reverse-complement node
        # (-s or -t) is present in the shown nodes. These edges can be drawn by
        # adjusting them to hit the RC node but on the opposite side as usual.
        self.inval_edge_info = cc.dc_inval_edge_info

        super().__init__(
            None,
            f"dc_{cc.name}",
            graph_utils.get_objs_by_ids(cc.nodes, cc.dc_shown_node_ids),
            graph_utils.get_objs_by_ids(cc.edges, cc.dc_shown_edge_ids),
            graph_utils.get_objs_by_ids(cc.patterns, cc.dc_shown_patt_ids),
            node_centric=cc.node_centric,
            length_field=cc.length_field,
            record_node_names=cc.record_node_names,
            count_positive_names=cc.count_positive_names,
        )

    def inval_edges_to_dot(self):
        out_dot = ""
        for e, inval_type, rn_id in self.inval_edge_info:
            if e.is_fake:
                # this should never happen, since showing a split node should
                # always mean we show its counterpart split node (so at no
                # point should a fake edge between X-L and X-R be invalidated
                # due to only ONE of these nodes being shown)
                raise WeirdError(f"Fake edge {e} is invalidated?")
            if inval_type == config.INVAL_SRC:
                out_dot += layout_utils.get_edge_dot(
                    rn_id, e.new_tgt_id, ports=("w", "w")
                )
            else:
                out_dot += layout_utils.get_edge_dot(
                    e.new_src_id, rn_id, ports=("e", "e")
                )
        return out_dot

    def inval_edges_to_cyjs(self, scope_settings, edgeid2ctrlpts=None):
        eles = []
        for e, inval_type, rn_id in self.inval_edge_info:
            j = e.to_cyjs(scope_settings)
            if inval_type == config.INVAL_SRC:
                j["data"]["source"] = rn_id
            else:
                j["data"]["target"] = rn_id
            layout_utils.try_add_control_points_to_cyjs(j, e, edgeid2ctrlpts)
            eles.append(j)
        return eles
