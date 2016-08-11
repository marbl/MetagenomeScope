# Settings that can be used to alter the output received by the script and
# by GraphViz.
# Generally, each variable or group of variables contains a explanatory
# comment above its declaration below. Default values are placed to the
# right of each variable.

from math import sqrt
import re

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

# If we opt not to use one or both of the bounds here, we can set these to
# float("inf") or float("-inf"), respectively.
MAX_CONTIG_AREA = 5
MIN_CONTIG_AREA = 0.5
MAX_CONTIG_HEIGHT = sqrt(MAX_CONTIG_AREA)
MIN_CONTIG_HEIGHT = sqrt(MIN_CONTIG_AREA)
WIDTH_HEIGHT_RATIO = 1.0
# The base we use when logarithmically scaling contigs based on length
CONTIG_SCALING_LOG_BASE = 100

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
GRAPH_STYLE      = ""

# Style applied to every node in the graph.
# NOTE -- fixedsize=true ensures accaccurate node scaling
GLOBALNODE_STYLE = ""

# Style applied to every edge in the graph.
# NOTE: "dir=none" gives "undirected" edges
GLOBALEDGE_STYLE = "headport=n,tailport=s"

# The filename suffixes indicating a file is of a certain type.
# Ideally, we should be able to detect what filetype an assembly file is by
# just examining the file's contents, but for now this is an okay workaround.
LASTGRAPH_SUFFIX = "LastGraph"
GRAPHML_SUFFIX   = ".gml"

# Regular expressions we use to parse .xdot (version 1.7) auto-generated
# files. You shouldn't need to modify these for most use cases.
GVNUMBER_RE = r'[\d\.e\+\-]+'

BOUNDBOX_RE = re.compile(r'bb="0,0,(%s),(%s)"' % (GVNUMBER_RE, GVNUMBER_RE))
CLUSDECL_RE = re.compile(r'subgraph cluster_(\w+)\s\{')
CLUS_END_RE = re.compile(r'(.+)\}')
NODEDECL_RE = re.compile(r'(c?\d+)\s+\[')
EDGEDECL_RE = re.compile(r'(c?\d+):[nsew]\s+->\s+(c?\d+):[nsew]\s+\[')
NDEG_END_RE = re.compile(r'(.+)\];')

NODEHGHT_RE = re.compile(r'height=(%s)' % (GVNUMBER_RE))
NODEWDTH_RE = re.compile(r'width=(%s)' % (GVNUMBER_RE))
NODEPOSN_RE = re.compile(r'pos="(%s),(%s)"' % (GVNUMBER_RE, GVNUMBER_RE))
NODESHAP_RE = re.compile(r'shape=(house|invhouse)')

# Regexes for detecting edge control points
CPTSTRNG_RE = r'[\d\.e\+\-\s]*'
CPTSDECL_RE = re.compile(r'_draw_="c 7 -#[\dABCDEF]{6} B ([\de\+\-]+) (%s)' % \
                    (CPTSTRNG_RE))
CPTS_NXL_RE = re.compile(r'(%s)' % (CPTSTRNG_RE))
CPTS_END_RE = re.compile(r'(.+)",')
