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
        self.cc_num = cc.cc_num

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
