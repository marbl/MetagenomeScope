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
####
# This file contains some utility functions that should help simplify the
# process of creating tests for MetagenomeScope's preprocessing script.

import os
import sqlite3
import random

from metagenomescope import main

INDIR = os.path.join("metagenomescope", "tests", "input")
OUTDIR = os.path.join("metagenomescope", "tests", "output")


def gen_args(graph_filename):
    """Generates a list of arguments for collate.run_script().

    Parameters
    ----------
    graph_filename : str
        filename of a graph in INDIR whose output will be placed in OUTDIR.

    Returns
    -------
    list
        List of arguments that can be passed directly to collate.run_script(),
        in the style of sys.argv[1:].

    Notes
    -----
    The only non-required arguments used in the generated list are -w (to
    overwrite existing output data) and -d (to put output in OUTDIR).

    It may be desirable to modify this function later to accept arbitrary
    arguments when testing those options.
    """
    return [
        "-i",
        os.path.join(INDIR, graph_filename),
        "-o",
        graph_filename,
        "-d",
        OUTDIR,
        "-w",
    ]


def create_and_open_db(graph_filename, extra_args=[]):
    """Runs collate; returns a connection and cursor for the produced .db file.

    TODO: add option to specify name for .db file? would be nice to have a
    one-to-one relationship of output .db files to tests (even if the same
    input graph is used in multiple tests), in order to ensure that any test's
    output (if fully generated, at least) can be visualized.

    Parameters
    ----------
    graph_filename : str
        filename of a graph in INDIR to use as input to the preprocessing
        script.
    extra_args : list
        list of extra arguments to be added to the input for
        collate.run_script(). The elements of this list should be strings.

    Returns
    -------
    (sqlite3.Connection, sqlite3.Cursor)
        A 2-tuple of a connection and cursor for the .db file produced by the
        preprocessing script.
    """
    collate.run_script(gen_args(graph_filename) + extra_args)
    connection = sqlite3.connect(os.path.join(OUTDIR, graph_filename + ".db"))
    cursor = connection.cursor()
    return connection, cursor


def is_oriented_graph(cursor):
    """Determines if the graph is oriented or unoriented.

    Parameters
    ----------
    cursor : sqlite3.Cursor
        A cursor for a .db file produced by the preprocessing script. You can
        obtain a cursor by calling create_and_open_db().

    Returns
    -------
    bool
        True if the graph is oriented (i.e. the contigs already have an
        assigned orientation, as with MetaCarvel output), False if the graph is
        unoriented (the contigs have no assigned orientation).

        Currently this is determined based on the filetype of the input graph,
        but eventually that should be independent of the filetype (so the user
        can do things like specify a GFA graph is oriented).
        See #67 and #71 on GitHub for details regarding work on that.
    """
    cursor.execute("SELECT filetype FROM assembly;")
    filetype = cursor.fetchone()[0]
    if filetype == "GML":
        return True
    return False


def validate_std_counts(cursor, node_ct, all_edge_ct, cc_ct):
    """Validates the number of standard-mode elements in the graph.

    Parameters
    ----------
    cursor : sqlite3.Cursor
        A cursor for a .db file produced by the preprocessing script. You can
        obtain a cursor by calling create_and_open_db().
    node_ct : int
        The expected number of nodes (contigs) in the graph. If the input
        assembly graph is unoriented, this will be interpreted as just the
        number of positive nodes; if the assembly graph is oriented, this will
        be interpreted as the total number of nodes.
        This will be compared with both
            1) the "assembly" table's node_count column and either
            2.1) the observed number of rows in the "nodes" table, or
            2.2) 0.5 * (the observed number of rows in the "nodes" table)
                (if the assembly graph is unoriented).
    all_edge_ct : int
        The expected number of edges in the graph, INCLUDING negative edges (in
        unoriented assembly graphs). This will be compared with both
            1) the "assembly" table's all_edge_count column and
            2) the observed number of rows in the "edges" table.
        For unoriented assembly graphs, note that this count should only
        contain self-implying edges once. See the comments below for details.
    cc_ct : int
        The expected number of weakly connected components in the graph. This
        will be compared with
            1) the "assembly" table's component_count column and
            2) the observed number of rows in the "components" table.

    Returns
    -------
    None

    Raises
    ------
    AssertionError
        If any of the above comparisons mentioned are not satisfied.
        Makes an additional check that edge_count == all_edge_count in oriented
        graphs, the failure of which will also cause an AssertionError.

        ALSO NOTE that, for graphs containing duplicate edges, the behavior of
        this test is undefined. Ideally duplicate edges should be ignored by
        the preprocessing script (see #75 on GitHub), but we aren't there yet.
        (Although once #75 is resolved, adding in a test case that features a
        graph with duplicate edges would be a good idea.)
    """
    is_oriented = is_oriented_graph(cursor)

    cursor.execute("SELECT node_count FROM assembly")
    assert cursor.fetchone()[0] == node_ct
    cursor.execute("SELECT COUNT(*) FROM nodes")
    if is_oriented:
        assert cursor.fetchone()[0] == node_ct
    else:
        assert (0.5 * cursor.fetchone()[0]) == node_ct

    # Explanation of what edge_count and all_edge_count mean:
    #
    # edge_count describes the number of "positive" edges in the graph. This is
    # equivalent to the total number of edges in the graph for oriented graphs,
    # and equivalent to half of the number of edges in the graph for unoriented
    # graphs (e.g. those contained in LastGraph files).
    #
    # all_edge_count describes the total number of edges in the graph. For
    # oriented graphs this should be equal to edge_count, and for unoriented
    # graphs this *should* be equal to 2 * edge_count. However, the latter case
    # can differ for unoriented graphs if the graph contains "self-implying
    # edges" -- that is, an edge from a given contig to its reverse complement
    # contig.
    #
    # This phenomenon is exhibited in loop.gfa (included as test input). We
    # only count each self-implying edge once in all_edge_count: this allows
    # us to obtain an accurate figure for the total number of edges in an
    # unoriented graph (because 2 * edge_count would be an overestimate for
    # graphs containing self-implying edges). Rendering the same edge twice
    # wouldn't really be helpful, and doesn't seem to be standard practice (see
    # https://github.com/fedarko/MetagenomeScope/issues/105 for discussion of
    # this.)
    cursor.execute("SELECT all_edge_count FROM assembly")
    assert cursor.fetchone()[0] == all_edge_ct
    cursor.execute("SELECT COUNT(*) FROM edges")
    assert cursor.fetchone()[0] == all_edge_ct

    # In oriented graphs, all_edge_count should equal edge_count.
    # In unoriented graphs, the two counts aren't necessarily relatable due to
    # the possibility of self-implying edges, as discussed above.
    if is_oriented:
        cursor.execute("SELECT edge_count FROM assembly")
        assert cursor.fetchone()[0] == all_edge_ct

    cursor.execute("SELECT component_count FROM assembly")
    assert cursor.fetchone()[0] == cc_ct
    cursor.execute("SELECT COUNT(*) FROM components")
    assert cursor.fetchone()[0] == cc_ct


def get_edge_map(cursor):
    """Returns a dict mapping source node IDs to a list of sink node IDs."""
    cursor.execute("SELECT * FROM edges")
    edge_map = {}
    for n in cursor:
        if n[0] not in edge_map:
            edge_map[n[0]] = [n[1]]
        else:
            edge_map[n[0]].append(n[1])
    return edge_map


def get_clusters(cursor):
    """Returns a list of clusters in the graph."""
    cursor.execute("SELECT * FROM clusters")
    return cursor.fetchall()


def get_cluster_type(cluster_row):
    """Returns the cluster type of a row retrieved from the "clusters" table.

    This is assumed to be the last column in the row, so if that changes then
    this test will break.
    """
    return cluster_row[len(cluster_row) - 1]


def get_cluster_frequencies(cursor):
    """Returns a dict mapping cluster types to their total frequencies."""
    clusters = get_clusters(cursor)
    cluster_type_2_freq = {}
    for c in clusters:
        ctype = get_cluster_type(c)
        if ctype not in cluster_type_2_freq:
            cluster_type_2_freq[ctype] = 1
        else:
            cluster_type_2_freq[ctype] += 1
    return cluster_type_2_freq


def gen_random_sequence(possible_lengths):
    """Generates a random DNA sequence with a length in the provided list."""

    seq_len = random.choice(possible_lengths)
    alphabet = "ACGT"
    seq = ""
    i = 0
    while i < seq_len:
        seq += random.choice(alphabet)
        i += 1
    return seq


def get_bicomponents(cursor):
    """Returns a list of bicomponents (-> SPQR trees) in the graph."""
    cursor.execute("SELECT * FROM bicomponents")
    return cursor.fetchall()


def get_metanodes(cursor):
    """Returns a list of SPQR tree metanodes in the graph."""
    cursor.execute("SELECT * FROM metanodes")
    return cursor.fetchall()


def get_children_of_metanode(cursor, metanode_id):
    """Given a metanode ID, returns a list of its child nodes."""
    cursor.execute(
        "SELECT * FROM singlenodes WHERE parent_metanode_id = ?",
        (metanode_id,),
    )
    return cursor.fetchall()


def get_root_metanode(cursor, bicomponent_id):
    """Given a bicomponent ID, returns its root metanode."""
    cursor.execute(
        "SELECT root_metanode_id FROM bicomponents " + "WHERE id_num = ?",
        (bicomponent_id,),
    )
    root_id = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM metanodes WHERE metanode_id = ?", (root_id,))
    return cursor.fetchone()
