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
# TODO test chains, 1-node cyclic chains, complex bubbles?

import os
import contextlib
from metagenomescope.tests import utils

EXTRAS = os.path.join(utils.INDIR, "extras")

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

def test_intersecting_paths_bubble():
    # Since the two paths in this bubble intersect, this is not a valid bubble.
    # Therefore, we should expect to see no structural patterns identified by
    # default.
    connection, cursor = \
            utils.create_and_open_db("intersecting_paths_bubble.gfa")

    with contextlib.closing(connection):
        utils.validate_std_counts(cursor, 6, 16, 2)
        cluster_type_2_freq = utils.get_cluster_frequencies(cursor)
        assert len(utils.get_clusters(cursor)) == 0

def test_user_defined_bubbles_and_frayed_ropes():
    # Let's say that we don't care about the intersecting paths thing from
    # test_intersecting_paths_bubble(), and we want to visualize it as a bubble
    # anyway.
    # Let's also say that we want the weird structure of {-6, -5, -4, -3, -2}
    # to be considered as a frayed rope, for some reason.

    def test_db_file(connection, cursor, has_other_frayed_rope=False):
        """Tests to make sure there's a bubble of {1,2,3,4,5,6}.

        Parameters
        ----------
            connection, cursor : sqlite3.Connection, sqlite3.Cursor
            has_other_frayed_rope : bool
                If true, tests to make sure there's a frayed rope at
                {-6, -5, -4, -3, -2}. If false, tests to make sure no other
                structural patterns besides the aforementioned bubble are
                present in the graph.

        (The bubbles described in ipb_up.txt and ipb_ub.txt are identical,
        which is why abstracting this code to this function works.)
        """
        with contextlib.closing(connection):
            # Test that we have only one identified bubble in the visualization
            cluster_type_2_freq = utils.get_cluster_frequencies(cursor)
            assert cluster_type_2_freq["Bubble"] == 1

            # Also check for the frayed rope
            if has_other_frayed_rope:
                assert cluster_type_2_freq["Frayed Rope"] == 1

            # Test that each node inside the marked bubble is actually inside
            # the bubble
            cursor.execute("SELECT id, parent_cluster_id FROM nodes")
            for obj in cursor.fetchall():
                if obj[0] in [str(x) for x in range(1, 7)]:
                    assert obj[1] != None
                    assert obj[1].startswith("B")
                elif not has_other_frayed_rope:
                    # NULL in sqlite3 is converted to None in Python: see
                    # https://docs.python.org/2/library/sqlite3.html#introduction
                    assert obj[1] == None
                else:
                    # If we've gotten here, obj[0] isn't in the identified
                    # bubble pattern and has_other_frayed_rope is True.
                    if obj[0] in [str(x) for x in range(-6, -1)]:
                        assert obj[1] != None
                        assert obj[1].startswith("F")
                    else:
                        # Still outside of any patterns.
                        assert obj[1] == None

    # First, let's try creating the bubble by using the user-specified bubbles
    # option (-ub). Although this option necessitates using a separate file
    # than the generic user-specified patterns file, it is useful because it
    # lets us use bubble file output generated by MetaCarvel (see
    # https://github.com/marbl/MetaCarvel/wiki/5.-Interpreting-the-output for a
    # description of what the bubbles.txt file format looks like) to augment
    # MetagenomeScope's simple bubble detection capabilities.
    ub_path = os.path.join(EXTRAS, "ipb_ub.txt")
    connection, cursor = \
            utils.create_and_open_db("intersecting_paths_bubble.gfa",
                    ["-ub", ub_path])
    test_db_file(connection, cursor)

    # Next, let's try this by defining a bubble as a user-specified pattern
    # using the -up option. This way is probably easier for users doing this
    # by hand, since you can store all the patterns you care about in one file
    # (instead of having to use a differently-formatted file for just your
    # bubbles).
    #
    # This also should create a frayed rope in the other component of the
    # graph, as discussed above.
    up_path = os.path.join(EXTRAS, "ipb_up.txt")
    connection, cursor = \
            utils.create_and_open_db("intersecting_paths_bubble.gfa",
                    ["-up", up_path])
    test_db_file(connection, cursor, has_other_frayed_rope=True)
