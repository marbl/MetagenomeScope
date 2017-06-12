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

# NOTE that changing MAX_COMPONENTS or MIN_COMPONENT_SIZE will result in
# strange behavior with those component ranks in the AsmViz viewer (see
# #35 on the GitHub page).
# Really, with the .db approach you should just be laying out all components at
# once. But as long as this config feature is still here, I figured a warning
# would be useful.
# How many connected components to display. Displays largest (by number of
# nodes) components first -- so MAX_COMPONENTS = 1 displays only the largest
# component, = 2 displays only the two largest components, etc.
# Setting this to None will just display all components.
# If MAX_COMPONENTS > the actual number of components in the graph, all
# components (with size >= MIN_COMPONENT_SIZE)  will be displayed.
MAX_COMPONENTS = None
# Minimum number of contigs for a connected component to be laid out by
# GraphViz. This is to avoid laying out a ton of small, unconnected groups
# of nodes.
# (If you want to lay out all connected components, even ones containing
# single nodes, then you can set MIN_COMPONENT_SIZE to 1.)
# As an example, if a graph contains 5 connected components:
# -One with 20 nodes
# -One with 10 nodes
# -One with  5 nodes
# -Two with  1 node each
# And MIN_COMPONENT_SIZE is set to 10, then even if MAX_COMPONENTS == None
# or MAX_COMPONENTS > 2, only the first two connected components will be
# displayed.
MIN_COMPONENT_SIZE = 1
# These are used directly in GraphViz, so they're in "inches". Granted, the
# .xdot file from GraphViz is used in the AsmViz viewer in Cytoscape.js, so
# "inches" are really an intermediate unit from our perspective.
# If we opt not to use one or both of the bounds here, we can set these to
# float("inf") or 0, respectively. However, I'd prefer to at least keep a lower
# bound of 1.0 on node height; that should help people who have trouble seeing
# things tell what's going in an assembly graph.
MAX_CONTIG_HEIGHT = 10
MIN_CONTIG_HEIGHT = 1
# The base we use when logarithmically scaling contig dimensions from length
CONTIG_SCALING_LOG_BASE = 10

### Frequently-used GraphViz settings ###
# More info on these available at www.graphviz.org/doc/info/attrs.html
# To make things simple, these constants don't use "exterior" semicolons
#
# NOTE that some of these values aren't used in the current version of
# collate.py, including the node group _SHAPE variables (originally used
# when we collapsed node groups before sending them to GraphViz) and the
# ROUNDED_..STYLE and CCOMPONENT_STYLE variables (ROUNDED_..STYLE vars.
# actually are applied in Node.node_info(), but they purposefully don't do
# anything to the graph as viewed in Cytoscape.js right now. We could maybe
# add some functionality re: that later).
BASIC_NODE_SHAPE = "invhouse"
RCOMP_NODE_SHAPE = "house"
SINGLE_NODE_SHAPE = "rectangle"
BUBBLE_STYLE     = "\tstyle=filled;\n\tfillcolor=cornflowerblue;\n"
FRAYEDROPE_STYLE = "\tstyle=filled;\n\tfillcolor=green;\n"
CHAIN_STYLE      = "\tstyle=filled;\n\tfillcolor=salmon;\n"
CYCLE_STYLE      = "\tstyle=filled;\n\tfillcolor=darkgoldenrod1;\n"

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
COLLATE_DESCRIPTION = "Prepare an assembly graph file for visualization, " + \
"generating a SQLite 3 database that can be loaded in the AsmViz viewer."
BUBBLE_SEARCH_MSG = "Looking for simple bubbles in the graph..."
SPQR_MSG = \
    "Generating SPQR tree decompositions for the bicomponents of the graph..."
SPQR_LAYOUT_MSG = \
    "Laying out SPQR trees for each bicomponent in the graph..."
SPQRVIEW_LAYOUT_MSG = \
    "Laying out a SPQR-tree-integrated view of the graph..."
BICOMPONENT_BUBBLE_SEARCH_MSG = \
    "Looking for complex bubbles in the graph using SPQR tree decompositions..."
FRAYEDROPE_SEARCH_MSG = "Looking for frayed ropes in the graph..."
CYCLE_SEARCH_MSG = "Looking for cyclic chains in the graph..."
CHAIN_SEARCH_MSG = "Looking for chains in the graph..."
COMPONENT_MSG = "Identifying connected components within the graph..."
READ_FILE_MSG = "Reading and parsing input file "
DB_INIT_MSG = "Initializing output file "
SAVE_AUX_FAIL_MSG = "Not saving "
LAYOUT_MSG = "Laying out "
SMALL_COMPONENTS_MSG = "small (containing < 5 nodes) remaining components..."
START_LAYOUT_MSG = "Laying out connected component "
DB_SAVE_MSG = "Saving information to "
DONE_MSG = "Done."
# Error messages (and occasional "helper" messages for constructing error msgs)
SEQ_NOUN = "Sequence "
NO_DNA_ERR = " does not contain a DNA sequence or length property"
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

# The filename suffixes indicating a file is of a certain type.
# Ideally, we should be able to detect what filetype an assembly file is by
# just examining the file's contents, but for now this is an okay workaround.
LASTGRAPH_SUFFIX = "lastgraph"
GRAPHML_SUFFIX   = "gml"
GFA_SUFFIX       = "gfa"
