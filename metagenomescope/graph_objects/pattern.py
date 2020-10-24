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


class Pattern(object):
    def __init__(self, pattern_id, pattern_type, node_ids):
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.node_ids = node_ids

    def __repr__(self):
        return "{} (ID {}) of nodes {}".format(
            self.pattern_type, self.pattern_id, self.node_ids
        )

    def layout(self, asm_graph):
        # TODO: need a way of associating node ids with if pattern or not
        # -> yeah, AssemblyGraph.is_pattern()
        # TODO: OH DANG also need access to the graph (for e.g. node lengths,
        # edges between nodes, etc.)? I guess we could have this method take in
        # the AssemblyGraph itself, so we could here access the digraph, etc.
        # Yeah that'd work.
        # TODO: actually do layout using dot, then store bounding box,
        # width/height, and assign node relative positions. I guess we should
        # keep track of namespace issues (e.g. what if nodes actually have 'x'
        # params \._./)
        # TODO: keep track of orientation for plain nodes. I guess add that to
        # the stuff stored in the nx dicts.
        raise NotImplementedError


class StartEndPattern(Pattern):
    def __init__(
        self, pattern_id, pattern_type, node_ids, start_node_id, end_node_id
    ):
        # NOTE: not recursive, but for now this is ok since at no point can
        # another pattern be the "real" start/end node of a bubble.
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        super().__init__(pattern_id, pattern_type, node_ids)

    def get_start_node(self):
        return self.start_node_id

    def get_end_node(self):
        return self.end_node_id
