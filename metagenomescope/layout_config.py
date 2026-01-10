###############################################################################
# Graphviz settings
###############################################################################

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

########
# Node scaling
########

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

########
# Graph style
########
# General graph style. Feel free to insert newlines/tabs for readability.
# Leaving this empty is also fine, if you just want default graph-wide settings
# Note that we rely on having a rankdir value of "TB" for the entire graph,
# in order to facilitate rotation in the .xdot viewer. (So I'd recommend not
# changing that unless you have a good reason.)
# Any text here must end without a semicolon.
GRAPH_STYLE = "rankdir=LR"


########
# Node style
########
# Note that this style impacts node groups in the "backfilled" layouts
# generated using -pg or -px, since node groups are temporarily represented as
# nodes.
#
# "fixedsize=true" is needed in order to prevent node labels from causing nodes
# to be resized. Might trigger some warnings from Graphviz but oh well, better
# that than nodes getting assigned the wrong sizes.
#
# "orientation=90" is needed in order to get nodes to be correctly
# rotated (to point in the left --> right direction), which makes the graph
# look as intended when rankdir=LR. Shoutouts to
# https://stackoverflow.com/a/45431027 for the wisdom that the node
# "orientation" attr existed.
GLOBALNODE_STYLE = "fixedsize=true,orientation=90"

# Whether or not to color in nodes in the drawings produced by dot (without
# having an effect on the viewer interface, since it doesn't care what colors
# dot says a node/node group is).
GLOBALNODE_STYLE += ',style=filled,fillcolor="#888888"'

########
# Edge style
########

# Style applied to every edge in the graph.
# Keeping headport=w,tailport=e is strongly recommended (assuming we keep
# rankdir=LR), since that impacts how edges are positioned and drawn in the
# graph (and the JS code expects edges to originate from nodes' "headports"
# and end at nodes' "tailports").
GLOBALEDGE_STYLE = "headport=w,tailport=e"

###############################################################################
# Client-side (i.e. done like within Cytoscape.js I guess?) layout settings
###############################################################################

# Dagre and fCoSE support animating the layout. I guess we might as well
# support this since it looks nice -- plus these layouts put all of the nodes
# in the same position at the start, so if we don't turn on animation then
# the user still sees this "flash of unstyled content" i guess
#
# Anyway, they have slightly different default duration settings, so let's
# standardize things here so that the user gets the same kinda experience
#
# (Actually controlling "animate" - whether or not we do animation at all -
# is controlled by a checkbox, which is controlled by
# ui_config.DEFAULT_DRAW_SETTINGS)
ANIMATION_SETTINGS = {
    "animationDuration": 500,
}
