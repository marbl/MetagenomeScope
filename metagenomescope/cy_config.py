###############################################################################
# Cytoscape.js configuration stuff
###############################################################################

# I just manually picked these from a hex color picker
RANDOM_COLORS = [
    "#880000",  # dark red
    "#aa5522",  # orange
    "#aa8822",  # gold
    "#99aa22",  # lemon-lime
    "#227711",  # forest green
    "#587562",  # olive drab, kinda
    "#117f7f",  # turquoise
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
