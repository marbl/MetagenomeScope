# Settings that can be used to alter the output received by the script and
# by GraphViz.
# Generally, each variable or group of variables contains a explanatory
# comment above its declaration below. Default values are placed to the
# right of each variable.

from math import sqrt

# This really shouldn't be messed with. Defines a dict of nucleotides to their
# complements that we can use when getting the reverse complement of a sequence
# from the GFA format.
COMPLEMENT = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
# The conversion factor between points (in GraphViz output) and inches, as used
# by GraphViz. By default GraphViz uses 72 points per inch, so changing this is
# not recommended. (This must be a float.)
POINTS_PER_INCH = 72.0

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
# Changing this causes strange things in the AsmViz viewer, since that's
# designed to work with node polygons of matching width and height.
# Keep it at 1.0 unless there's a good reason.
WIDTH_HEIGHT_RATIO = 1.0
# The base we use when logarithmically scaling contigs based on length
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
BUBBLE_SHAPE     = "square"                        # we don't use these now
FRAYEDROPE_SHAPE = "square"                        # we don't use these now
CHAIN_SHAPE      = "square"                        # we don't use these now
CYCLE_SHAPE      = "square"                        # we don't use these now
ROUNDED_UP_STYLE = "style=filled,fillcolor=gray64" # we don't use these now
ROUNDED_DN_STYLE = "style=filled,fillcolor=black"  # we don't use these now
CCOMPONENT_STYLE = "style=filled,fillcolor=red"    # we don't use these now
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
GRAPH_STYLE      = "xdotversion=1.7"

# Style applied to every node in the graph.
# We use fixedsize here because the default node label, "\N", actually makes
# the node's id/name its label -- so fixedsize prevents this from influencing
# node dimensions.
GLOBALNODE_STYLE = "fixedsize=true"

# Style applied to every edge in the graph.
# NOTE: "dir=none" gives "undirected" edges
GLOBALEDGE_STYLE = "headport=n,tailport=s"

# Style applied (directly) to every cluster in the graph.
GLOBALCLUSTER_STYLE = "margin=0"

# Prefixes of certain messages that are output to the user at
# certain points in the script's processing. Each message is followed by the
# size rank of the connected component in question, which is in turn followed
# by some punctuation (either an ellipsis (...) or a period (.)).
START_LAYOUT_MSG = "Laying out connected component "
DONE_LAYOUT_MSG = "Done laying out connected component "
START_PARSING_MSG = "Parsing layout of connected component "
DONE_PARSING_MSG = "Done parsing layout of connected component "

# The filename suffixes indicating a file is of a certain type.
# Ideally, we should be able to detect what filetype an assembly file is by
# just examining the file's contents, but for now this is an okay workaround.
LASTGRAPH_SUFFIX = "lastgraph"
GRAPHML_SUFFIX   = "gml"
GFA_SUFFIX       = "gfa"
