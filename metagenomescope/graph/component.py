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

from .subgraph import Subgraph


class Component(Subgraph):
    """Represents a weakly connected component in an assembly graph."""

    def __init__(self, unique_id):
        """Initializes this Component object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other Components) integer ID of this
            Component.
        """
        self.unique_id = unique_id

        # unique size rank index of this component (the cc in the graph with
        # the most nodes has size rank 1, the next biggest one has size rank 2,
        # etc). We store this to make searching through the graph easier.
        self.cc_num = None
        super().__init__()

    def __repr__(self):
        return f"Component {self.unique_id}: {self._get_repr_counts()}"

    def set_cc_num(self, cc_num):
        """Updates the component number of this component and its children."""
        self.cc_num = cc_num
        for obj in self.get_objs():
            obj.set_cc_num(cc_num)
