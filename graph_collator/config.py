# Copyright (C) 2017 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
# Settings that can be used to alter the output received by the script and
# by GraphViz.
# Generally, each variable or group of variables contains a explanatory
# comment above its declaration below. Default values are placed to the
# right of each variable.

from math import sqrt
import stat

# This really shouldn't be messed with. Defines a dict of nucleotides to their
# complements that we can use when getting the reverse complement of a sequence
# from the GFA format.
COMPLEMENT = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
# The conversion factor between points (in GraphViz output) and inches, as used
# by GraphViz. By default GraphViz uses 72 points per inch, so changing this is
# not recommended. (This must be a float.)
POINTS_PER_INCH = 72.0

# File mode used for auxiliary files (.gv/.xdot)
# This should match up with the defaults on most systems.
AUXMOD = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

# The base we use when logarithmically scaling contig dimensions from length
CONTIG_SCALING_LOG_BASE = 10
# The minimum/maximum lengths of either side of a node.
# These are used directly in GraphViz, so they're in "inches". Granted,
# "inches" are really an intermediate unit from our perspective since they're
# converted to pixels in the viewer interface's code.
# If we opt not to use one or both of the bounds here, we can set these to
# float("inf") or 0, respectively. However, I'd prefer to at least keep a lower
# bound of 1.0 on node height; that should help people who have trouble seeing
# things tell what's going in an assembly graph.
MAX_CONTIG_DIM = 10
MIN_CONTIG_DIM = 1

### Frequently-used GraphViz settings ###
# More info on these available at www.graphviz.org/doc/info/attrs.html
BASIC_NODE_SHAPE = "invhouse"
RCOMP_NODE_SHAPE = "house"
SINGLE_NODE_SHAPE = "rectangle"

### Global graph settings (applied to every node/edge/etc. in the graph) ###
# General graph style. Feel free to insert newlines for readability.
# Leaving this empty is also fine, if you just want default graph-wide settings
# Note that we rely on having a rankdir value of "TB" for the entire graph, 
# in order to facilitate rotation in the .xdot viewer. (So I'd recommend not
# changing that unless you have a good reason.)
# Any text here must end without a semicolon.
GRAPH_STYLE      = "xdotversion=1.7;\n\toverlap=false"

# Style applied to every node in the graph.
# Keeping label="" is strongly recommended -- otherwise, node sizes will change
# to accommodate labels, which throws off the usefulness of scaling to indicate
# contig/scaffold length. You could set fixedsize=true to allow for labels
# within the .gv/.xdot output, but that can cause warnings due to the resulting
# labels not having enough room for certain nodes.
GLOBALNODE_STYLE = "label=\"\""

# Style applied to every edge in the graph.
# NOTE: "dir=none" gives "undirected" edges
GLOBALEDGE_STYLE = "headport=n,tailport=s"

# Style applied (directly) to every cluster in the graph.
GLOBALCLUSTER_STYLE = "margin=0"

# Various status messages/message prefixes that are displayed to the user.
# Displayed during command-line argument parsing
COLLATE_DESCRIPTION = "Prepares an assembly graph file for visualization, " + \
    "generating a database file that can be loaded in the MetagenomeScope " + \
    "viewer interface."
USERBUBBLES_SEARCH_MSG = "Identifying user-specified bubbles in the graph..."
USERPATTERNS_SEARCH_MSG = "Identifying user-specified misc. patterns in " + \
    "the graph..."
BUBBLE_SEARCH_MSG = "Looking for simple bubbles in the graph..."
SPQR_MSG = \
    "Generating SPQR tree decompositions for the bicomponents of the graph..."
SPQR_LAYOUT_MSG = \
    "Laying out SPQR trees for each bicomponent in the graph..."
BICOMPONENT_BUBBLE_SEARCH_MSG = \
    "Looking for complex bubbles in the graph using SPQR tree decompositions..."
FRAYEDROPE_SEARCH_MSG = "Looking for frayed ropes in the graph..."
CYCLE_SEARCH_MSG = "Looking for cyclic chains in the graph..."
CHAIN_SEARCH_MSG = "Looking for chains in the graph..."
COMPONENT_MSG = "Identifying connected components within the graph..."
EDGE_SCALING_MSG = "Scaling edge thicknesses in each connected component..."
READ_FILE_MSG = "Reading and parsing input file "
DB_INIT_MSG = "Initializing output file "
SAVE_AUX_FAIL_MSG = "Not saving "
LAYOUT_MSG = "Laying out "
SMALL_COMPONENTS_MSG = "small (containing < 5 nodes) remaining components..."
SPQR_COMPONENTS_MSG = " SPQR-integrated component "
START_LAYOUT_MSG = "Laying out connected component "
DB_SAVE_MSG = "Saving information to "
DONE_MSG = "Done."
# Error messages (and occasional "helper" messages for constructing error msgs)
SEQ_NOUN = "Sequence "
NO_DNA_ERR = " does not contain a DNA sequence or length property"
DUPLICATE_ID_ERR = "Duplicate node ID: "
FILETYPE_ERR = "Invalid input filetype; see README for accepted file types"
EDGE_CTRL_PT_ERR = "Invalid GraphViz edge control points"
NO_FN_ERR = "No filename provided for "
ARG_ERR = "Invalid argument: "
NO_FN_PROVIDED_ERR = "No input and/or output file name provided"
EXISTS_AS_NON_DIR_ERR = " already exists as a non-directory file"
IS_DIR_ERR = " is a directory"
EXISTS_ERR = " already exists and -w is not set"
EMPTY_LIST_N50_ERR = "N50 of an empty list does not exist"
N50_CALC_ERR = "N50 calculation error"
UBUBBLE_NODE_ERR = "User-specified bubble file contains invalid node "
UPATTERN_NODE_ERR = "User-specified pattern file contains invalid node "
UBUBBLE_ERR_PREFIX = "User-specified bubble \""
UPATTERN_ERR_PREFIX = "User-specified pattern "
CONTIGUOUS_ERR = "\" is not contiguous"
LABEL_EXISTENCE_ERR = \
    "Can't use -ubl or -upl options for a graph type with no node labels"

# The filename suffixes indicating a file is of a certain type.
# Ideally, we should be able to detect what filetype an assembly file is by
# just examining the file's contents, but for now this is an okay workaround.
LASTGRAPH_SUFFIX = "lastgraph"
GRAPHML_SUFFIX   = "gml"
GFA_SUFFIX       = "gfa"
