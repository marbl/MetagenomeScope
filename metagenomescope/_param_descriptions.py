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
    "Assembly graph file. We accept GFA, FASTG, DOT, GML, and LastGraph files."
)

OUTPUT_DIR = (
    "If provided, we'll save an interactive visualization of the graph to "
    "this directory. The directory will contain an index.html file; you can "
    "open this file in a web browser to access the visualization. If we "
    "cannot create this directory for some reason (e.g. it already exists), "
    "we'll raise an error."
)

OUTPUT_DOT = (
    "If provided, we'll save a DOT file describing the graph to this "
    "filepath. Identified patterns will be represented in this DOT file as "
    '"cluster" subgraphs.'
)

OUTPUT_CCSTATS = (
    "If provided, we'll save a tab-separated values (TSV) file describing the "
    "numbers of nodes, edges, and structural patterns in each connected "
    "component of the graph to this filepath."
)

ASSUME_ORIENTED = (
    "Assume that the nodes in a graph are already oriented, and doesn't "
    "create duplicates. This will only work with graphs where, for every "
    "node, its reverse complement node is not present in the same connected "
    "component; if this is the case for any node, then an error will be "
    "raised. THIS OPTION ISN'T FINISHED YET!"
)

MAX_DEETS = (
    "Impacts all output options (-o, -od, -os). Setting this to 0 removes "
    "this limit."
)

MAXN = (
    "We will not consider connected components containing more nodes than "
    "this. This option is given here because hierarchical graph layout is "
    "relatively slow for large/tangled components, and because our "
    "visualization interface becomes slow when drawing lots of nodes / edges. "
    f"{MAX_DEETS}"
)

MAXE = (
    "We will not visualize connected components containing more edges than "
    "this. Functions analogously to --max-node-count. Setting this to 0 "
    f"removes this limit. {MAX_DEETS}"
)

PATTERNS_FLAG = (
    "If --patterns is set, we'll identify structural patterns (e.g. bubbles) "
    "in the graph and highlight these in the visualization. If --no-patterns "
    'is set, we won\'t do this (and will just visualize the "original" graph '
    "structure)."
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
