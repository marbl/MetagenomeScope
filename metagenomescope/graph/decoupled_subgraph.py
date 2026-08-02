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


class DecoupledSubgraph(Subgraph):
    """Represents a decoupled subgraph."""

    def __init__(self, sg):
        """Initializes this object.

        Parameters
        ----------
        sg: Subgraph
        """
        if not sg.decoupling_done:
            raise WeirdError(f"{sg} not decoupled?")

        # If sg is a Component, set the same component number for this obj --
        # so it is sorted properly by DrawResults.get_sorted_regions()
        if hasattr(sg, "cc_num"):
            self.cc_num = sg.cc_num

        # Lump shown Edges and InvalidatedEdges together, which makes
        # downstream stuff easier to think about -- less special-casing needed.
        # (We defer doing this to here in order to avoid having to store extra
        # stuff all the time, I guess ...?)
        edges = graph_utils.filter_objs_by_ids(sg.edges, sg.dc_shown_edge_ids)
        edges += sg.dc_inval_edges

        super().__init__(
            None,
            f"dc_{sg.name}",
            graph_utils.filter_objs_by_ids(sg.nodes, sg.dc_shown_node_ids),
            edges,
            graph_utils.filter_objs_by_ids(sg.patterns, sg.dc_shown_patt_ids),
            node_centric=sg.node_centric,
            length_field=sg.length_field,
            record_node_names=sg.record_node_names,
            count_positive_names=sg.count_positive_names,
        )
