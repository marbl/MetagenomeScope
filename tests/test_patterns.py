#!/usr/bin/env python
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
# Runs various tests for the preprocessing script. Assumes the CWD is
# MetagenomeScope/.
#
# Maybe I'll later make this run tests for the viewer interface.
#
# These are nowhere near comprehensive yet; a TODO is to write more (#76).
#
# TODO use Travis-CI?

import sys
sys.path.append("graph_collator/")
import collate
import os
import sqlite3

INDIR = os.path.join("tests", "input")
OUTDIR = os.path.join("tests", "output")

def gen_args(graph_filename):
    """Generates a list of arguments for collate.run_script(), given the
       filename of a graph in INDIR whose output will be placed in OUTDIR.

       Uses no extraneous parameters besides -w (to overwrite existing output
       data).
    """
    return ["-i", os.path.join(INDIR, graph_filename), "-o",
            graph_filename, "-d", OUTDIR, "-w"]

def create_and_open_db(fn):
    """Runs collate, and then creates a connection and cursor."""

    collate.run_script(gen_args(fn))
    connection = sqlite3.connect(os.path.join(OUTDIR, fn + ".db"))
    cursor = connection.cursor()
    return connection, cursor

def get_edge_map(cursor):
    """Returns a dict mapping each node ID that has at least one outgoing edge
       to a list of all the node IDs to which these edges go.
    """
    cursor.execute("SELECT * FROM edges")
    edge_map = {}
    for n in cursor:
        if n[0] not in edge_map:
            edge_map[n[0]] = [n[1]]
        else:
            edge_map[n[0]].append(n[1])
    return edge_map

def test_cyclic_chain():
    # 1 -> 2
    # 2 -> 1
    # (implies also that -2 -> -1 and -1 -> -2)
    connection, cursor = create_and_open_db("cycletest_LastGraph")

    # Check that edges are correct
    edge_map = get_edge_map(cursor)
    assert edge_map["1"] == ["2"] and edge_map["2"] == ["1"]
    assert edge_map["-2"] == ["-1"] and edge_map["-1"] == ["-2"]

    # Check that the .db file contains exactly 2 clusters, each of which is a
    # cyclic chain
    cursor.execute("SELECT * FROM clusters")
    cluster_ct = 0
    for n in cursor:
        assert n[len(n) - 1] == "Cyclic Chain"
        cluster_ct += 1
    assert cluster_ct == 2

    connection.close()

def test_bubble():
    # 1 -> 2, 2 -> 4
    # 1 -> 3, 3 -> 4
    connection, cursor = create_and_open_db("bubble_test.gml")

    # Check edge validity
    edge_map = get_edge_map(cursor)
    assert "2" in edge_map["1"] and "3" in edge_map["1"]
    assert "4" in edge_map["2"] and "4" in edge_map["3"]

    # Check that the .db file contains exactly 1 cluster, which is a bubble
    cursor.execute("SELECT * FROM clusters")
    cluster_ct = 0
    for n in cursor:
        if cluster_ct == 0:
            assert n[len(n) - 1] == "Bubble"
        cluster_ct += 1
    assert cluster_ct == 1

    connection.close()
