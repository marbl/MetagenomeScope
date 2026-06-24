###############################################################################
# General settings
###############################################################################

# The amount of indentation to use for each level in DOT files. You could also
# use a \t character here, if you're the sort of person who prefers tabs ._.
INDENT = "  "

UNIT_GV_INCHES = "in"
UNIT_GV_POINTS = "pt"
UNIT_CY_PIXELS = "px"

# Conversion factor between inches and points (both in Graphviz), per
# https://graphviz.org/doc/info/attrs.html.
#
# Graphviz node widths / heights, etc. are in inches, but Graphviz positions
# are in points (and Graphviz says there are 72 points per inch).
#
# Because of how the recursive layout algorithm works (with inferring
# positions based on bounding boxes, etc), we need to be able to accurately
# convert between points and inches. Thus, we use exactly 72 here. This
# resolves the ugly inconsistencies that using 54 for this introduced: see
# https://github.com/marbl/MetagenomeScope/issues/398.
POINTS_PER_INCH = 72

# The conversion factor between inches (Graphviz) and pixels (Cytoscape.js),
# currently used ONLY FOR adjusting the scale of nodes (from inches -> px).
#
# You can use 72 for this if you'd like (so that you only have to think in
# terms of inches and points), but this results in a lot of edges being marked
# as bad edges by Cytoscape.js -- and the nodes look really big in the
# visualization. I am not sure why this is the case...? See the Velvet E. coli
# graph for an example: using 72 pixels per inch there are 97 bad edges in cc1
# with default settings, but using 54 pixels per inch there are 0 bad edges in
# cc1 with default settings. Weird!
#
# In theory, edge control points are not another sort of thing we need to think
# about here -- since we convert them from literal points to relative points
# between node positions, right...? But maybe nodes being bigger or smaller
# could cause weird stuff here.
#
# Anyway, currently (as of June 2026), we use this ONLY for the final step of
# converting node dimensions from inches to Cytoscape.js values. This seems to
# make everything Just Work (tm).
PIXELS_PER_INCH = 54

########
# Node scaling
########

# The base we use when logarithmically scaling contig dimensions from length
NODE_SCALING_LOG_BASE = 10

# Divide node areas by this much. Doesn't impact NOLENGTH_NODE_* sizes;
# only matters for nodes with a defined length.
#
# Because we divide *all* node areas in the drawing by this same value, it
# doesn't really matter beyond impacting how other stuff (edge thicknesses,
# font sizes) looks in the context of nodes.
#
# Previously this was 10, but then I increased it to 12 to account for how
# pentagonal nodes are a bit bigger after the changes in
# https://github.com/marbl/MetagenomeScope/pull/455 ...
NODE_AREA_DIVISOR = 12

NOLENGTH_NODE_WIDTH = 0.4
NOLENGTH_NODE_HEIGHT = 0.4

########
# Graph style
########
# General graph style. Feel free to insert newlines/tabs for readability.
# Any text here must end without a semicolon.
PROG2GRAPHSTYLE = {"dot": "rankdir=LR", "sfdp": "overlap=prism"}

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
GLOBALEDGE_STYLE = ""

# fake edges
FAKEEDGE_STYLE = 'style="dashed"'

# back edges (from an end node to a start node of a single pattern)
# this prevents these edges from impacting node ranking, which makes
# cyclic chains look much nicer - see
# https://github.com/marbl/MetagenomeScope/issues/368
# and https://stackoverflow.com/a/6826107
BACKEDGE_STYLE = 'constraint="false"'

# If all of the control points of an edge are close enough to the straight
# line from source to target, then we won't bother drawing the edge using its
# control points -- we'll just mark it a basic bezier or something. This value
# controls how close "close enough" is.
CTRL_PT_DIST_EPSILON = 10

########
# Cluster (pattern) style
########

# used for the "padding" style in Cy.js and subgraph "margin". Cytoscape.js is
# not clear on what the default padding is but this seems to match it -- based
# on going through its codebase and noticing
# https://github.com/cytoscape/cytoscape.js/blob/57e681a052d79c02f6e9fa802ff0c9ce9a77ff3e/snippets/animated-bfs.js#L56
# NOTE: this is not currently used in recursive layout. Maybe the way to
# handle that would be adjusting the "pad" setting for the entire graph when
# laying out subregions...?
CLUSTER_PADDING = 10

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
# ui_config.DEFAULT_MODIFIER_SETTINGS)
ANIMATION_SETTINGS = {
    "animationDuration": 500,
}
