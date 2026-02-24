###############################################################################
# Control panel
###############################################################################

CONTROLS_FG_COLOR = "#ccc"
CONTROLS_BG_COLOR = "#123"
CONTROLS_BORDER_COLOR = "#002"

# width of the control panel
# This should ensure that -- on big screens -- the control panel is limited to
# a reasonable 20em width, but on small screens the control panel takes up
# at most 50% of the screen width. This seems reasonable to me (and this is
# probs overkill now that we are using a server-side approach where people
# prooobably won't be using this on phones/tablets).
#
# NOTE: if you modify this, you should also update the .offscreen-controls
# class definition in assets/viewer.css accordingly in order to negate this.
CONTROLS_WIDTH = "min(20em, 50%)"

# thickness of borders throughout the control panel
CONTROLS_BORDER_THICKNESS = "1em"

# "sub-header" thickness
CONTROLS_SUB_BORDER_THICKNESS = "0.25em"

# duration for hiding/showing ctrl panel, moving it and the graph accordingly
CONTROLS_TRANSITION_DURATION = "0.2s"

###############################################################################
# Selected element tables
###############################################################################
ELE_TBL_CLASSES = "ag-theme-balham-dark fancytable"
BADGE_CLASSES = "ms-1"
BADGE_ZERO_COLOR = "primary"
BADGE_SELECTED_COLOR = "#96183c"
BADGE_AVAILABLE_COLOR = "#6c1ddb"

###############################################################################
# Info dialog
###############################################################################

# classes on the info dialog's tables
INFO_DIALOG_TABLE_CLASSES = "table table-striped-columns"

###############################################################################
# Drawing options dialog
###############################################################################

# default classes on the algorithm descriptions
ALG_DESC_CLASSES = "layout-alg-desc"

###############################################################################
# Path settings
###############################################################################

PATH_SETTINGS_PARENT_CLASSES = "form-check fancyChecklist"
