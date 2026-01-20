###############################################################################
# Graphviz settings
###############################################################################

# The amount of indentation to use for each level in DOT files. You could also
# use a \t character here, if you're the sort of person who prefers tabs ._.
INDENT = "  "

# The conversion factor between inches (Graphviz) and pixels (Cytoscape.js).
# There is a lot of history to this, and I think Cytoscape.js has changed its
# system from points to pixels??? Or maybe it was always in pixels and graphviz
# has just been kind of inconsistent with its units being in points or inches
# depending on bounding boxes or coordinates??? let's just see how things go
PIXELS_PER_INCH = 72

########
# Node scaling
########

# The base we use when logarithmically scaling contig dimensions from length
NODE_SCALING_LOG_BASE = 10

NOLENGTH_NODE_WIDTH = 0.4
NOLENGTH_NODE_HEIGHT = 0.4

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

# Colors in nodes in the drawings produced by dot (without having an effect on
# the interactive visualization in Cy.js, which doesn't care what colors dot
# says things are)
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

FAKEEDGE_STYLE = 'style="dashed"'

# If all of the control points of an edge are close enough to the straight
# line from source to target, then we won't bother drawing the edge using its
# control points -- we'll just mark it a basic bezier or something. This value
# controls how close "close enough" is.
CTRL_PT_DIST_EPSILON = 5

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
