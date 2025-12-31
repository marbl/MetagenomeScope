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
DEFAULT_EDGE_COLORING = COLORING_RANDOM

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
PATH_TBL_CC_COL = "O"

###############################################################################
# Tables of selected elements
###############################################################################

NODE_TBL_NAME_COL = "N"

EDGE_TBL_SRC_COL = "S"
EDGE_TBL_TGT_COL = "T"

PATT_TBL_ID_COL = "I"
PATT_TBL_TYPE_COL = "T"
PATT_TBL_NCT_COL = "N"
PATT_TBL_ECT_COL = "E"
PATT_TBL_PCT_COL = "P"

# Maps "internal" names for node / edge properties to human-readable names, and
# AG Grid cellDataType parameters.
# (As we add on more filetype parsers, feel free to extend these structures.)
NODEATTR2HRT = {
    "name": ("ID", "text"),
    "length": ("Length", "text"),
    "orientation": ("+/-", "text"),
    "depth": ("Cov.", "number"),
    "cov": ("Cov.", "number"),
    "gc": ("GC Content", "number"),
    "gc_content": ("GC Content", "number"),
}

EDGEATTR2HRT = {
    # Ideally we'd be more precise about what exactly these are the mean and
    # standard deviation of, but i am not completely sure. I think they
    # represent the "mean and standard deviation for the implied distance
    # between a pair of contigs," to quote the MetaCarvel paper? But they could
    # also represent "the library size (mean and standard deviation)," maybe,
    # so for the sake of avoiding being wrong I am being conservative for now
    "mean": ("Mean", "number"),
    "stdev": ("\u03c3", "number"),
    "orientation": ("Orient.", "text"),
    "bsize": ("BSize", "number"),
    "multiplicity": ("Multiplicity", "number"),
    "id": ("ID", "text"),
    "approx_length": ("~Length", "number"),
    "cov": ("Cov.", "number"),
    "color": ("Color", "text"),
    "first_nt": ("First nt", "text"),
    "kmer_cov": ("k-mer cov.", "number"),
}

# some attributes are obvious and/or not worth showing in the selected element
# tables, since there is not a lot of space. Record these here.
NODEATTRS_SKIP = ("orientation",)
EDGEATTRS_SKIP = ("color", "dir")
