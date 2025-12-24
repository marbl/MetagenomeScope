###############################################################################
# Default drawing settings
###############################################################################

# value of the draw settings checklist indicating that yes, we do want to
# show patterns in the visualization
SHOW_PATTERNS = "patterns"
# by default, the following draw settings are enabled. (... currently we only
# have "Show patterns" as an option here, but probs we will add more later)
DEFAULT_DRAW_SETTINGS = ["patterns"]

COLORING_RANDOM = "random"
COLORING_UNIFORM = "uniform"

DEFAULT_NODE_COLORING = COLORING_RANDOM
DEFAULT_EDGE_COLORING = COLORING_UNIFORM

SCREENSHOT_PNG = "png"
SCREENSHOT_JPG = "jpg"
SCREENSHOT_SVG = "svg"
DEFAULT_SCREENSHOT_FILETYPE = SCREENSHOT_PNG

###############################################################################
# Component size rank selection
###############################################################################

# In theory we could support "--" without too much work, but ... that gives
# me the heebie jeebies
RANGE_DASHES = ("-", "\u2013", "\u2014")

###############################################################################
# Treemap in the graph info dialog
###############################################################################

# if a graph has < this many components, then don't bother aggregating its
# components in the treemap
MIN_LARGE_CC_COUNT = 100

# Don't label components with >= this many nodes as small
# (see https://github.com/marbl/MetagenomeScope/issues/278)
MIN_NONSMALL_CC_NODE_COUNT = 50

###############################################################################
# Table of paths
###############################################################################

# these are just the IDs of the columns, we'll come up with something fancier
# for the UI. Since these apparently need to be repeated once for every row in
# rowData, let's use shorter strings to reduce the amount of space we need...?
# probably won't matter tho
PATH_TBL_NAME_COL = "N"
PATH_TBL_COUNT_COL = "C"

###############################################################################
# Tables of selected elements
###############################################################################

NODE_TBL_NAME_COL = "N"
