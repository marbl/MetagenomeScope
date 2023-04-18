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
# This file defines various variables that can be used to alter the behavior
# of the preprocessing script. See the comments associated with each
# variable/group of variables for more information.

import stat

# The conversion factor between points (in GraphViz output) and inches, as used
# by GraphViz. GraphViz uses 72 points per inch, but here we use 63
# points per inch -- this is kind of a compromise. In old versions of
# MetagenomeScope, at times we would pass inch values (for node / pattern
# widths and heights) directly to the JS interface and have that code do the
# conversion using an INCHES_TO_PIXELS value of 54 -- which was inconsistent,
# since things like edge control points were just stored as points and not
# converted to pixels.
#
# We now do all the conversions in the Python code, but
# I've noticed that using the 72 points-per-inch value for nodes kinda squishes
# the graph too much, making things look gross. (Some of the edge arrows for
# bubbles don't even show up in the interface.) Using a smaller value helps a
# bit -- using 54 for this spaces out the graph a bit too much, and using the
# midpoint between 54 and 72 (63) seems ok. Since this really scales _all_
# distances in the graph, I think, changing this value doesn't change the
# intepretation of the graph -- at least for node sizes, it seems to rescale
# all nodes. But I should really try to formally look into this sometime...
POINTS_PER_INCH = 63.0

# File mode used when creating "auxiliary" files directly in the
# preprocessing script (collate.py). Possible auxiliary files
# that can be generated by the preprocessing script include:
#
# -> *_links and *_single_links files describing edges in a graph
# -> bubbles.txt, chains.txt, etc.: files listing all patterns in a graph
# -> *_nobackfill.gv files describing the graph in the DOT format without
#    backfilling being used (generated by -nbdf)
# -> *.gv files describing the graph in the DOT format (generated by -pg)
# -> *.xdot files describing the graph in the XDOT format (generated by -px)
#
# Note that this doesn't impact the permissions on component_*.info and
# spqr*.gml files, since those files are generated by the SPQR script. It also
# shouldn't impact the permissions on .db files, since those are generated by
# SQLite. (Also, .db files aren't really considered "auxiliary" since they're
# the main output of the script.)
#
# For a description of what these permissions mean, see
# http://www.physics.udel.edu/~bnikolic/teaching/phys660/RUTE/rute/node17.html.
# For a description of which of these stat flags correspond to these
# permissions, see https://docs.python.org/2/library/stat.html.
#
# This is currently set to give files the 0644 permission, but you can
# definitely modify this if you'd like.
AUXMOD = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

# The base we use when logarithmically scaling contig dimensions from length
NODE_SCALING_LOG_BASE = 10
# The minimum/maximum area of a node.
# These variables are used directly in GraphViz, so they're technically in
# "inches". That being said, "inches" are really an intermediate unit from our
# perspective since (at least as of writing) they're converted to points and
# then passed directly to Cytoscape.js. See POINTS_PER_INCH above for details.
MAX_NODE_AREA = 10
MIN_NODE_AREA = 1
NODE_AREA_RANGE = MAX_NODE_AREA - MIN_NODE_AREA
# Proportions of the "long side" of a contig, for various levels of contigs in
# the graph.
# Used for the lower 25% (from 0% to 25%) of contigs in a component
LOW_LONGSIDE_PROPORTION = 0.5
# Used for the middle 50% (from 25% to 75%) of contigs in a component
MID_LONGSIDE_PROPORTION = 2.0 / 3.0
# Used for the upper 25% (from 75% to 100%) of contigs in a component
HIGH_LONGSIDE_PROPORTION = 5.0 / 6.0

# Factor by which collapsed node groups' dimensions are scaled
# As with the dimensions of Node objects in the preprocessing script, these
# will be switched in the viewer interface (due to the graph being rotated)
# -- so _W_ refers to the vertical dimension of the node group, and _H_
# refers to the horizontal dimension.
COLL_CL_W_FAC = 1.0 / 2.0
COLL_CL_H_FAC = 1.0 / 2.0

### Frequently-used GraphViz settings ###
# More info on these available at www.graphviz.org/doc/info/attrs.html

NODE_ORIENTATION_TO_SHAPE = {"+": "invhouse", "-": "house"}

### Global graph settings (applied to every node/edge/etc. in the graph) ###
#
# NOTE that most of the current settings here are important for keeping the
# drawings generated by MetagenomeScope "consistent," so changing these around
# could result in strange-looking output.
#
# General graph style. Feel free to insert newlines/tabs for readability.
# Leaving this empty is also fine, if you just want default graph-wide settings
# Note that we rely on having a rankdir value of "TB" for the entire graph,
# in order to facilitate rotation in the .xdot viewer. (So I'd recommend not
# changing that unless you have a good reason.)
# Any text here must end without a semicolon.
GRAPH_STYLE = "xdotversion=1.7"
# Useful for visualizing .gv files. Shouldn't impact the viewer interface's
# visualization -- only impacts dot's drawings.
# GRAPH_STYLE = "xdotversion=1.7;\n\toverlap=false;\n\tdpi=30;\n\trotate=90"

# Style applied to every node in the graph.
#
# Note that this style also impacts node groups in the "backfilled" layouts
# generated using -pg or -px, since node groups are temporarily represented as
# nodes.
#
# Keeping label="" is strongly recommended -- otherwise, node sizes will change
# to accommodate labels, which throws off the usefulness of scaling to indicate
# contig/scaffold length. You could set fixedsize=true to allow for labels
# within the .gv/.xdot output, but that can cause warnings due to the resulting
# labels not having enough room for certain nodes.
GLOBALNODE_STYLE = 'label=""'
# Whether or not to color in nodes in the drawings produced by dot (without
# having an effect on the viewer interface, since it doesn't care what colors
# dot says a node/node group is).
# Since this will impact node groups in backfilled layouts, if you use this
# style it's recommended that you also set COLOR_PATTERNS to True. (Otherwise,
# the backfilled layouts' drawings generated by dot will color all node groups
# #888888.)
#
# NOTE that COLOR_NODES and COLOR_PATTERNS are both set to True in order to
# generate Figs. 3 and 4 in the MetagenomeScope paper, so these config options
# should be left in this file so those figures can be replicated.
COLOR_NODES = True
# The actual style addition is kept separate from COLOR_NODES to make it easy
# to toggle this behavior and reference the toggling of this behavior
if COLOR_NODES:
    GLOBALNODE_STYLE += ',style=filled,fillcolor="#888888"'

# Style applied to every edge in the graph.
# NOTE: "dir=none" gives "undirected" edges
# Keeping headport=n,tailport=s is strongly recommended, since that impacts how
# edges are positioned and drawn in the graph (and the viewer interface code
# expects # edges to originate from nodes' "headports" and end at nodes'
# "tailports").
GLOBALEDGE_STYLE = "headport=n,tailport=s"

# Style applied (directly) to every cluster in the graph.
# Keeping margin=0 is strongly recommended, since otherwise cluster bounding
# boxes can take up extra space in the graph (the resulting drawings would also
# not mesh well with the viewer interface, where compound nodes are drawn with
# a zero margin).
GLOBALCLUSTER_STYLE = "margin=0"

### Other misc. config variables ###
# Whether or not to specify colors for node groups in .gv/.xdot files. If this
# is True, then PATTERN2COLOR is used to set the colors.
COLOR_PATTERNS = True
# All of these colors are based on the default pattern colors in the viewer
# interface as of June 20, 2018.
# The exception to this is "other_structural_patterns", which shouldn't ever
# be a pattern object's plural_name attribute (NodeGroups should never be
# directly created). If this ever happens, though, the resulting pattern will
# be colored black.
PATTERN2COLOR = {
    "bubbles": "#9abaf3",
    "frayed_ropes": "#59f459",
    "chains": "#eedddd",
    "cyclic_chains": "#ffd163",
    "misc_patterns": "#c398eb",
    "other_structural_patterns": "#000000",
}

# The default values for -maxn and -maxe in the collate script.
MAXN_DEFAULT = 7999
MAXE_DEFAULT = 7999

# Used to add an extra line below the first logging message, and just before
# the last logging message.
SEPARATOR_CHAR = "-"

# Maps "internal" names for node / edge properties to human-readable ones.
# This is passed on to the JavaScript code, so that the UI there can use these
# human-readable names.
# (As we add on more filetype parsers, feel free to extend these structures.)
NODEATTR2HR = {
    "name": "ID",
    "length": "Length",
    "orientation": "Orientation",
    "depth": "Coverage",
    "cov": "Coverage",
    "gc": "GC Content",
    "gc_content": "GC Content",
}
EDGEATTR2HR = {
    # Ideally we'd be more precise about what exactly these are the mean and
    # standard deviation of, but i am not completely sure. I think they
    # represent the "mean and standard deviation for the implied distance
    # between a pair of contigs," to quote the MetaCarvel paper? But they could
    # also represent "the library size (mean and standard deviation)," maybe,
    # so for the sake of avoiding being wrong I am being conservative for now
    "mean": "Mean",
    "stdev": "Standard Deviation",
    "bsize": "Bundle Size",
    "multiplicity": "Multiplicity",
    "id": "ID",
    "approx_length": "Approximate Length",
    "cov": "Coverage",
    "color": "Color",
    "first_nt": "First Nucleotide",
    "kmer_cov": "k-mer Coverage",
}

# Used as the suffixes of split nodes.
SPLIT_SEP = "-"
SPLIT_LEFT = "L"
SPLIT_RIGHT = "R"

# Pattern types -- used internally.
PT_BUBBLE = 0
PT_CHAIN = 1
PT_CYCLICCHAIN = 2
PT_ROPE = 3

# Maps pattern types to human-readable names.
PT2HR = {
    PT_BUBBLE: "Bubble",
    PT_CHAIN: "Chain",
    PT_CYCLICCHAIN: "Cyclic Chain",
    PT_FRAYEDROPE: "Frayed Rope",
}

# Various status messages/message within the graph prefixes that are displayed
# to the user.
USERBUBBLES_SEARCH_MSG = "Identifying user-specified bubbles in the graph..."
USERPATTERNS_SEARCH_MSG = (
    "Identifying user-specified misc. patterns in " + "the graph..."
)
SPQR_MSG = (
    "Generating SPQR tree decompositions for the bicomponents of the graph..."
)
SPQR_LAYOUT_MSG = "Laying out SPQR trees for each bicomponent in the graph..."
BICOMPONENT_BUBBLE_SEARCH_MSG = (
    "Looking for complex bubbles in the graph using SPQR tree "
    "decompositions..."
)
DB_INIT_MSG = "Initializing output file "
SAVE_AUX_FAIL_MSG = "Not saving "
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
IS_DIR_ERR = " is a directory"
EXISTS_ERR = " already exists and -w is not set"
EMPTY_LIST_N50_ERR = "N50 of an empty list does not exist"
N50_CALC_ERR = "N50 calculation error"
UBUBBLE_NODE_ERR = "User-specified bubble file contains invalid node "
LINE_NOUN = "Line "
UBUBBLE_NOTENOUGH_ERR = " of user-specified bubble file defines no child nodes"
UPATTERN_NOTENOUGH_ERR = (
    " of user-specified pattern file defines no child nodes"
)
UPATTERN_NODE_ERR = "User-specified pattern file contains invalid node "
UBUBBLE_ERR_PREFIX = 'User-specified bubble "'
UPATTERN_ERR_PREFIX = 'User-specified pattern "'
CONTIGUOUS_ERR = '" is not contiguous'
LABEL_EXISTENCE_ERR = (
    "Can't use -ubl or -upl options for a graph type with no node labels"
)
