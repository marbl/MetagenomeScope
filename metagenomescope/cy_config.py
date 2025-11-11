###############################################################################
# Cytoscape.js configuration stuff
###############################################################################

# I just manually picked these from a hex color picker
RANDOM_COLORS = [
    "#880000",
    "#aa5522",
    "#aa8822",
    "#99aa22",
    "#227711",
    "#117733",
    "#117777",
    "#111177",
    "#220077",
    "#441177",
    "#771166",
    "#771144",
    "#771122",
]

NODE_COLOR = "#888888"
UNSELECTED_NODE_FONT_COLOR = "#eeeeee"
SELECTED_NODE_BLACKEN = "0.5"
SELECTED_NODE_FONT_COLOR = "#eeeeee"

EDGE_COLOR = "#555555"
# ideally we would use something like background-blacken to just darken
# edges by some amount regardless of what color they are, but cy.js does
# not seem to support this. the easy solution is just using a fixed dark
# color for edges, even if they are colorized as something at the moment
# (maybe we can make this fancier later)
SELECTED_EDGE_COLOR = "#000000"

FWD_NODE_POLYGON_PTS = "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1"
REV_NODE_POLYGON_PTS = "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1"
UNORIENTED_NODE_SHAPE = "circle"
