#!/usr/bin/env python3.6
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

INPUT = (
    "Assembly graph file to be visualized. GFA, FASTG, LastGraph (Velvet), "
    "and GML (MetaCarvel) file formats are accepted."
)

OUTPUT_DIR = (
    "Directory in which all output files will be stored. The index.html file "
    "within this directory contains the graph visualization. "
    "If this directory already exists, or it otherwise cannot be created, "
    "an error will be raised."
)

ASSUME_ORIENTED = (
    "Assume that the nodes in a graph are already oriented, and doesn't "
    "create duplicates. This will only work with graphs where, for every "
    "node, its reverse complement node is not present in the same connected "
    "component; if this is the case for any node, then an error will be "
    "raised. THIS OPTION ISN'T FINISHED YET!"
)

MAXN = (
    "Connected components with more nodes than this value will not be "
    "laid out or available for display in the visualization. Since "
    "hierarchical graph layout is relatively slow for large or tangled "
    "connected components, this is a heuristic to enable visualization "
    "of the other regions of graphs with a few 'hairball' components."
)

MAXE = (
    "Connected components with more edges than this value will not be "
    "laid out or available for display in the visualization. Functions "
    "analogously to --max-node-count."
)

# TODO: actually change way this works so that -ubl always true
MBF = (
    "File describing pre-identified bubbles in the graph, in the format "
    "of MetaCarvel's bubbles.txt output: each line of the file is formatted "
    "as (source label)(tab)(sink label)(tab)(all node labels in the bubble, "
    "including source and sink labels, all separated by tabs). Please see the "
    "MetaCarvel documentation at https://github.com/marbl/MetaCarvel for "
    "more details on MetaCarvel. This option can only be used if the input "
    "graph is a MetaCarvel GML file; otherwise, this will raise an error."
)

UP = (
    "File describing any pre-identified structural patterns in the graph: "
    "each line of the file should be formatted as "
    "(pattern type)(tab)(all node IDs in the pattern, all separated by tabs). "
    "If (pattern type) is 'Bubble' or 'Frayed Rope', then the pattern will be "
    "represented in the visualization as a Bubble or Frayed Rope, "
    "respectively; otherwise, the pattern will be represented as a generic "
    "'misc. user-specified pattern,' and colored accordingly in the "
    "visualization."
)

SPQR = (
    "Compute data for the SPQR 'decomposition modes' in the visualization. "
    "Necessitates a few additional system requirements; see MetagenomeScope's "
    "installation instructions wiki page for details."
)


STRUCTPATT = (
    "Save .txt files containing node information for all structural patterns "
    "identified in the graph."
)

PG = (
    "Save all .gv (DOT) files generated for nontrivial (i.e. containing > 1 "
    "node, or at least 1 edge or node group) connected components."
)

PX = "Save all .xdot files generated for nontrivial connected components."

NBDF = (
    'Saves .gv (DOT) files without cluster "backfilling" for each '
    "nontrivial connected component in the graph."
)

NPDF = (
    "Saves .gv (DOT) files without any structural pattern information "
    "embedded."
)
