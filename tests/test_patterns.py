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
####Y
# Runs various tests for the preprocessing script. Assumes the CWD is
# MetagenomeScope/.
#
# Maybe I'll later make this run tests for the viewer interface.
#
# These are nowhere near comprehensive yet; a TODO is to write more.
#
# TODO use pytest and Travis-CI?

import sys
sys.path.append("graph_collator/")
import collate
import os
import sqlite3

INDIR = os.path.join("tests", "input")
OUTDIR = os.path.join("tests", "output")

def gen_args(graph_filename):
    """Generates a list of arguments for collate.run_script(), given the
       filename of a graph in testgraphs/.
    """
    return ["-i", os.path.join(INDIR, graph_filename), "-o",
            graph_filename, "-d", OUTDIR, "-w"]

def test_cyclic_chain():
    # 1 -> 2
    # 2 -> 1
    # (implies also that -2 -> -1 and -1 -> -2)
    fn = "cycletest_LastGraph"
    collate.run_script(gen_args(fn))
    connection = sqlite3.connect(os.path.join(OUTDIR, fn + ".db"))
    cursor = connection.cursor()
    # Check that the .db file only specifies 4 edges, and that those
    # edges are correct
    cursor.execute("SELECT * FROM edges")
    edge_map = {}
    for n in cursor:
        edge_map[n[0]] = n[1]
    assert len(edge_map) == 4
    assert edge_map["1"] == "2" and edge_map["2"] == "1"
    assert edge_map["-2"] == "-1" and edge_map["-1"] == "-2"
    # Check that the .db file contains exactly 2 clusters, each of which is a
    # cyclic chain
    cursor.execute("SELECT * FROM clusters")
    cluster_ct = 0
    for n in cursor:
        assert n[len(n) - 1] == "Cyclic Chain"
        cluster_ct += 1
    assert cluster_ct == 2
