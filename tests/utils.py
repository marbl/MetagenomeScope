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
# This file contains some utility functions that should help simplify the
# process of creating tests for MetagenomeScope's preprocessing script.

import os
import sys
import sqlite3

sys.path.append("graph_collator")
import collate

INDIR = os.path.join("tests", "input")
OUTDIR = os.path.join("tests", "output")

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
    return ["-i", os.path.join(INDIR, graph_filename), "-o",
            graph_filename, "-d", OUTDIR, "-w"]

def create_and_open_db(graph_filename):
    """Runs collate; returns a connection and cursor for the produced .db file.

    Parameters
    ----------
    graph_filename : str
        filename of a graph in INDIR to use as input to the preprocessing
        script.

    Returns
    -------
    (sqlite3.Connection, sqlite3.Cursor)
        A 2-tuple of a connection and cursor for the .db file produced by the
        preprocessing script.
    """
    collate.run_script(gen_args(graph_filename))
    connection = sqlite3.connect(os.path.join(OUTDIR, graph_filename + ".db"))
    cursor = connection.cursor()
    return connection, cursor

def validate_edge_count(cursor, num_edges):
    """Validates the number of edges in the graph.

    Parameters
    ----------
    cursor : sqlite3.Cursor
        A cursor for a .db file produced by the preprocessing script. You can
        obtain a cursor by calling create_and_open_db().
    num_edges : int
        The expected number of edges in the graph. This will be compared with
        both 1) the "assembly" table's all_edge_count column and
             2) the observed number of rows in the "edges" table.

    Returns
    -------
    None

    Raises
    ------
    AssertionError
        If either of the two conditions mentioned in the parameter description
        for num_edges are not satisifed.
    """
    cursor.execute("SELECT all_edge_count FROM assembly")
    assert cursor.fetchone()[0] == num_edges
    cursor.execute("SELECT COUNT(source_id) FROM edges")
    assert cursor.fetchone()[0] == num_edges

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
