from statistics import mean
from math import sqrt

###############################################################################
# General Cytoscape.js settings
###############################################################################

BG_COLOR = "#ffffff"

# Flye and LJA have defined colors for edges, and some of these are not
# recognized by Cy.js (e.g. "aquamarine1"). I think we could PROBABLY look up
# the X11 colors and use those somehow but whatever let's just manually handle
# these
#
# https://github.com/mikolmogorov/Flye/blob/886b8c17412cdf3a2868a28237bca6c5ad1da156/src/repeat_graph/output_generator.cpp#L261-L265
# https://github.com/AntonBankevich/LJA/blob/2815f838f01527facceeb77b6eea997a6aaed0b4/src/lib/spoa/src/graph.cpp#L625
GVCOLOR2HEX = {
    "red": "#ff0000",
    "darkgreen": "#005f00",
    "blue": "#0000ff",
    "goldenrod": "#daa520",
    "goldenrod1": "#ffc125",
    "cadetblue1": "#90e9f2",
    "darkorchid": "#9932cc",
    "aquamarine1": "#7fffd4",
    "darkgoldenrod1": "#ffb90f",
    "deepskyblue1": "#00b5f2",
    "darkolivegreen3": "#a2cd5a",
    "black": "#000000",
    "grey": "#797979",
}

###############################################################################
# Nodes
###############################################################################

# I just manually picked these from a hex color picker
# For testing, https://lawlesscreation.github.io/hex-color-visualiser/ is
# super useful
RANDOM_COLORS = [
    "#ee0000",  # light red
    "#cc0000",  # darker red
    "#cc5555",  # kinda washed out terracotta red
    "#ef9058",  # lighter orange
    "#e35f10",  # light orange
    "#aa5522",  # dark orange
    "#985932",  # moldy apricot. that was the first term that came to mind
    "#aa8822",  # gold
    "#93792b",  # darker gold
    "#697608",  # dark lemon-lime (ordinary lemon-lime was too hard to see)
    "#2a8717",  # forest green
    "#22aa22",  # partially bulldozed forest green
    "#61806c",  # olive drab, kinda
    "#119f9f",  # turquoise
    "#148f8f",  # darker turquoise
    "#6363bb",  # medium blueish (purposefully avoiding #00f - selection color)
    "#6f6fa3",  # blue gray ish
    "#9169e0",  # dull light purple
    "#b243f5",  # bright purple, sorta
    "#c71461",  # kinda pinkish red
    "#a30f9e",  # fuschia?
    "#e34fdc",  # brighter fuschia (basically pink)
    "#86624c",  # light brown
    "#73503b",  # darker brown
    "#999999",  # light gray
    "#787878",  # dark gray
]

NODE_COLOR = "#888888"
NODE_FONT_COLOR = "#000000"
SELECTED_NODE_BORDER_COLOR = "#0000ff"
SELECTED_NODE_BORDER_WIDTH = 8

# used to distinguish ordinary nodes from pattern nodes based on data dict
# from the selectedNodeData callback alone
NODE_DATA_TYPE = "N"

###############################################################################
# Node shapes
###############################################################################


def pts2spp(pts, dx=0, mx=1, autocenter=False):
    """Converts a list of [x, y] points into a "x1 y1 x2 y2 ..." string.

    These kinds of strings are the format in which Cytoscape.js accepts
    shape-polygon-points settings.

    Parameters
    ----------
    dx: float
        Defaults to 0. You can adjust this to to shift the x coordinates
        by some value.

    mx: float
        Defaults to 1. You can adjust this to multiply each (x + dx) coordinate
        by some value. (So, like, each x value is set to "mx * (x + dx)".)

    autocenter: bool
        Defaults to False. If True, we'll compute the average x coordinate "A"
        across all of these points, and then set dx equal to -A (in order
        to center this shape at x = 0). Note that this will have the effect
        of overriding whatever you had initially set dx to, and that this
        will be applied before applying mx.

    Returns
    -------
    str
    """
    if autocenter:
        avg_x = mean([p[0] for p in pts])
        dx = -avg_x
    return " ".join(f"{mx * (p[0] + dx)} {p[1]}" for p in pts)


########
# Shapes for "oriented" nodes (i.e. the pentagon-looking things)
########

# Non-split node shapes. These should correspond to the "invhouse" / "house"
# shapes in Graphviz: https://graphviz.org/doc/info/shapes.html#polygon
fwd_pentagon_pts = [[-1, 1], [0.23587, 1], [1, 0], [0.23587, -1], [-1, -1]]
rev_pentagon_pts = [[-x, y] for (x, y) in fwd_pentagon_pts]

FWD_NODE_SPLITN_POLYGON_PTS = pts2spp(fwd_pentagon_pts)
REV_NODE_SPLITN_POLYGON_PTS = pts2spp(rev_pentagon_pts)

# For a split forward node, the left split becomes a rectangle
#  and the right split becomes a triangle pointing right.
fwd_pentagon_triangle_pts = [[-1, 1], [1, 0], [-1, -1]]
FWD_NODE_SPLITR_POLYGON_PTS = pts2spp(fwd_pentagon_triangle_pts)

# It's the opposite for a split reverse node: now, the right split is a
# rectangle and the left split is a triangle.
REV_NODE_SPLITL_POLYGON_PTS = pts2spp(fwd_pentagon_triangle_pts, mx=-1)

########
# Node shapes for "unoriented" nodes (i.e. circles)
########
# Note that the split node shapes for fwd/rev nodes above fill the
# entirety of the shape-polygon-points bounding box. This is not the
# case for semicircles, which only take up half of the box. We'll account
# for this in NodeLayout.set_dims().

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

# Now we'll define the bottom-left quarter of the circle. Since it is symmetric
# to the top-left quarter, we can reuse our work from above and avoid redoing
# all of these sqrt operations (not that this will be a bottleneck, though...)
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
# (We could also use autocenter=True for pts2spp, but I already know we need
# to move this by 0.5 so whatever. Also depending on how much stuff is in
# xcoords the average x coordinate might be a bit off from 0.5, in which case
# autocenter=True may give a slightly different translation.)

left_semicircle_full_centered = [
    [x + 0.5, y] for (x, y) in left_semicircle_top + left_semicircle_bot
]

UNORIENTED_NODE_SPLITL_POLYGON_PTS = pts2spp(left_semicircle_full_centered)

# For drawing a right semicircle, just negate the x coordinates. We could also
# do this before the + 0.5 operation above, in which case we would need (for
# each left semicircle x-coordinate x) to compute rightversion(x) = -x - 0.5,
# in order to apply the analogous centering operation for the right semicircle.
# Since -(x + 0.5) = -x - 0.5, we get the same result either way, so we can
# just be lazy and negate the x coordinates after the + 0.5 operation.
UNORIENTED_NODE_SPLITR_POLYGON_PTS = pts2spp(
    left_semicircle_full_centered, mx=-1
)

###############################################################################
# Edges
###############################################################################

EDGE_COLOR = "#555555"
SELECTED_EDGE_COLOR = "#5555ff"
SELECTED_EDGE_WIDTH = "8"

FAKE_EDGE_LINE_STYLE = "dashed"
FAKE_EDGE_LINE_DASH_PATTERN = ["5", "9"]
FAKE_EDGE_WIDTH = "8"
SELECTED_FAKE_EDGE_WIDTH = "10"

EDGE_FONT_COLOR = "#000000"
SELECTED_EDGE_FONT_COLOR = "#000000"

###############################################################################
# Patterns
###############################################################################
# (the colors are set in config.py's PT2COLOR variable)

UNSELECTED_PATTERN_BORDER_WIDTH = 2
UNSELECTED_PATTERN_BORDER_COLOR = "#000000"
SELECTED_PATTERN_BORDER_WIDTH = 8
SELECTED_PATTERN_BORDER_COLOR = "#0000ff"

PATTERN_DATA_TYPE = "P"

###############################################################################
# Labels
###############################################################################

# in em
DEFAULT_LABEL_FONT_SIZE = 1

# for nodes, edges, and patterns
LABEL_STYLE = {
    "label": "data(label)",
    # this is in px
    "min-zoomed-font-size": "12",
}

# just nodes
NODE_LABEL_STYLE = {
    "text-valign": "center",
}

# just patterns
PATTERN_LABEL_STYLE = {
    "text-valign": "top",
}
