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
# Tests some basic structual pattern identification functionality.
# TODO test chains, complex bubbles, user-specified bubbles/patterns (esp.
# when we resolve #100)

import contextlib
import utils

def test_cyclic_chain():
    # 1 -> 2
    # 2 -> 1
    # (implies also that -2 -> -1 and -1 -> -2)
    connection, cursor = utils.create_and_open_db("cycletest_LastGraph")

    # CODELINK using just "with connection" has different behavior than closing
    # the connection. To automatically close the connection after the with
    # block, we use contextlib.closing().
    # For more information, see https://stackoverflow.com/a/19524679.
    with contextlib.closing(connection):
        utils.validate_std_counts(cursor, 2, 4, 2)
        edge_map = utils.get_edge_map(cursor)
        assert edge_map["1"] == ["2"] and edge_map["2"] == ["1"]
        assert edge_map["-2"] == ["-1"] and edge_map["-1"] == ["-2"]

        # Check that the .db file contains exactly 2 clusters, each of which is a
        # cyclic chain
        clusters = utils.get_clusters(cursor)
        assert len(clusters) == 2
        for c in clusters:
            assert utils.get_cluster_type(c) == "Cyclic Chain"

def test_bubble():
    # 1 -> 2, 2 -> 4
    # 1 -> 3, 3 -> 4
    connection, cursor = utils.create_and_open_db("bubble_test.gml")

    with contextlib.closing(connection):
        utils.validate_std_counts(cursor, 4, 4, 1)
        edge_map = utils.get_edge_map(cursor)
        assert "2" in edge_map["1"] and "3" in edge_map["1"]
        assert "4" in edge_map["2"] and "4" in edge_map["3"]

        # Check that the .db file contains exactly 1 cluster, which is a bubble
        clusters = utils.get_clusters(cursor)
        assert len(clusters) == 1
        assert utils.get_cluster_type(clusters[0]) == "Bubble"

def test_longpatterns():
    connection, cursor = utils.create_and_open_db("longtest_LastGraph")

    with contextlib.closing(connection):
        utils.validate_std_counts(cursor, 36, 72, 8)
        cluster_type_2_freq = utils.get_cluster_frequencies(cursor)
        assert cluster_type_2_freq["Bubble"] == 4
        assert cluster_type_2_freq["Frayed Rope"] == 4
