# Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
####
# Tests the SPQR tree decomposition functionality in MetagenomeScope.

import pytest
import contextlib
from metagenomescope.tests import utils

@pytest.mark.spqrtest
def test_spqr_tree_structure():
    connection, cursor = utils.create_and_open_db("marygold_fig2a.gml",
            ["-spqr", "-nt"])
    # We only identify 1 simple bubble in the MaryGold graph. However,
    # using SPQR tree decompositions, we can see that there's actually a sort
    # of nested bubble structure inherent to the graph.
    assert utils.get_cluster_frequencies(cursor)["Bubble"] == 1
    bicmps = utils.get_bicomponents(cursor)
    assert len(bicmps) == 1
    assert len(utils.get_metanodes(cursor)) == 7
    # For context: the [0][0] is intended to 1) extract the row describing the
    # only bicomponent in this graph, and then 2) extract the ID (which is the
    # first parameter in the row) of the bicomponent.
    # The final [0] extracts the ID of the root metanode (which we obtained via
    # fetchone() in utils.get_root_metanode() -- that's why it's not in a
    # collection of rows, and we can just use one [0] there)
    root_id = utils.get_root_metanode(cursor, bicmps[0][0])[0]
    children_of_root = utils.get_children_of_metanode(cursor, root_id)
    assert len(children_of_root) == 6
    ids_seen = set()
    for c in children_of_root:
        ids_seen.add(c[0])
    assert ids_seen == set(["10", "11", "1", "5", "6", "9"])
    # TODO test structure of SPQR tree beyond root node -- will necessitate
    # a function that just returns a dict representing the structure of the
    # full tree and the child nodes of each metanode, which we can then run
    # some set comparisons on like above.
