from math import sqrt

###############################################################################
# Nodes
###############################################################################

# I just manually picked these from a hex color picker
RANDOM_COLORS = [
    "#880000",  # dark red
    "#aa5522",  # orange
    "#aa8822",  # gold
    "#99aa22",  # lemon-lime
    "#227711",  # forest green
    "#587562",  # olive drab, kinda
    "#119f9f",  # turquoise
    "#111177",  # dark blue
    "#4411aa",  # royal purple. is that a color? yeah i think so
    "#661199",  # magenta
    "#c71461",  # kinda pinkish red
    "#a30f9e",  # fuschia
    "#826a5b",  # light brown
    "#382403",  # deep brown
]

NODE_COLOR = "#888888"
UNSELECTED_NODE_FONT_COLOR = "#eeeeee"
SELECTED_NODE_BLACKEN = "0.5"
SELECTED_NODE_FONT_COLOR = "#eeeeee"

########
# Node shapes for "oriented" nodes (i.e. the pentagon-looking things)
########

# Non-split node shapes. These should correspond to the "invhouse" / "house"
# shapes in Graphviz: https://graphviz.org/doc/info/shapes.html#polygon
FWD_NODE_SPLITN_POLYGON_PTS = "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1"
REV_NODE_SPLITN_POLYGON_PTS = "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1"

# For a split forward node, the left split becomes a rectangle (we can just
# use Cytoscape.js' built-in "rectangle" shape) and the right split becomes
# a triangle (pointing right).
FWD_NODE_SPLITR_POLYGON_PTS = "-1 1 1 0 -1 -1"

# It's the opposite for a split reverse node: now, the right split is a
# rectangle and the left split is a triangle.
REV_NODE_SPLITL_POLYGON_PTS = "1 1 -1 0 1 -1"

########
# Node shapes for "unoriented" nodes (i.e. circles)
########
# The formula for a circle with radius 1 centered on (0, 0) is
# x^2 + y^2 = 1. We want to just get points from half of this circle.

# First, we will define the top-left quarter of the circle. This is
# centered on (0, 0) still, so we will trace out x values from x = 0
# to x = -1. You can add or remove entries to this list in order to
# increase or decrease the smoothness of the semicircle.
xcoords = [
    0,
    -0.1,
    -0.2,
    -0.3,
    -0.4,
    -0.5,
    -0.6,
    -0.7,
    -0.8,
    -0.9,
    -0.95,
    -0.98,
    -1,
]

# Okay, now compute y coordinates for the above x coordinates.
left_semicircle_top = [[x, sqrt(1 - x**2)] for x in xcoords]

# Now we'll define is the bottom-left quarter of the circle. Since it is
# symmetric to the top-left quarter, we can reuse our work from above and
# avoid redoing all of these sqrt operations (not that this will be a
# bottleneck, though...)
# The [:-1] slices off the last coordinate in the top half [-1, 0] because
# there is no need to duplicate that.
# The [::-1] reverses the points, since now we are starting at x = -1
# and going back to x = 0.
left_semicircle_bot = [[x, -y] for (x, y) in left_semicircle_top[:-1]][::-1]

# The points above are represent the left half of a circle centered on (0, 0),
# which means that the center point of this semicircle is roughly at (-0.5, 0).
#
# When you tap on / select a node in Cytoscape.js, a semitransparent rounded
# box appears around this node. These semicircles look a bit off-center in
# relation to this box, because the shape-polygon-points conventions in
# Cytoscape.js assume that the node shape is centered at (0, 0).
#
# So! We can fix this by just moving this shape to the right by x = 0.5. This
# centers the semicircle within the bounding box.

left_semicircle_full_centered = [
    [x + 0.5, y] for (x, y) in left_semicircle_top + left_semicircle_bot
]

UNORIENTED_NODE_SPLITL_POLYGON_PTS = " ".join(
    f"{c[0]} {c[1]}" for c in left_semicircle_full_centered
)

# For drawing a right semicircle, just negate the x coordinates. We could also
# do this before the + 0.5 operation above, in which case we would need (for
# each left semicircle x-coordinate x) to compute rightversion(x) = -x - 0.5,
# in order to apply the analogous centering operation for the right semicircle.
# Since -(x + 0.5) = -x - 0.5, we get the same result either way, so we can
# just be lazy and negate the x coordinates after the + 0.5 operation.
UNORIENTED_NODE_SPLITR_POLYGON_PTS = " ".join(
    f"{-c[0]} {c[1]}" for c in left_semicircle_full_centered
)

###############################################################################
# Edges
###############################################################################

EDGE_COLOR = "#555555"
# ideally we would use something like background-blacken to just darken
# edges by some amount regardless of what color they are, but cy.js does
# not seem to support this. the easy solution is just using a fixed dark
# color for edges, even if they are colorized as something at the moment
# (maybe we can make this fancier later)
SELECTED_EDGE_COLOR = "#000000"

FAKE_EDGE_LINE_STYLE = "dashed"
FAKE_EDGE_DASH_PATTERN = ["5", "9"]

###############################################################################
# Patterns
###############################################################################

# matches "cornflowerblue" in graphviz
BUBBLE_COLOR = "#9abaf3"
# matches "green2" in graphviz
FRAYEDROPE_COLOR = "#59f459"
# this one used to match "salmon" in graphviz (#fcaca3 i think?) and then i
# changed it to be less flashy since there are a lot of chains involved
# in hierarchical decomp stuff and i want people to take this seriously
CHAIN_COLOR = "#eedddd"
# matches "darkgoldenrod1" in graphviz
CYCLICCHAIN_COLOR = "#ffd163"

UNSELECTED_PATTERN_BORDER_WIDTH = "2"
UNSELECTED_PATTERN_BORDER_COLOR = "#000000"
SELECTED_PATTERN_BORDER_WIDTH = "5"
SELECTED_PATTERN_BORDER_COLOR = "#000000"
