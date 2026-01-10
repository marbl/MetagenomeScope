###############################################################################
# Default drawing settings
###############################################################################

# value of the draw settings checklist indicating that yes, we do want to
# show patterns in the visualization
SHOW_PATTERNS = "patterns"
DO_LAYOUT_ANIMATION = "animate"

# by default, these draw settings are enabled --
DEFAULT_SHOW_PATTERNS = True
DEFAULT_DO_LAYOUT_ANIMATION = True
DEFAULT_DRAW_SETTINGS = []
if DEFAULT_SHOW_PATTERNS:
    DEFAULT_DRAW_SETTINGS.append(SHOW_PATTERNS)
if DEFAULT_DO_LAYOUT_ANIMATION:
    DEFAULT_DRAW_SETTINGS.append(DO_LAYOUT_ANIMATION)

COLORING_RANDOM = "random"
COLORING_UNIFORM = "uniform"

DEFAULT_NODE_COLORING = COLORING_RANDOM
DEFAULT_EDGE_COLORING = COLORING_RANDOM

SCREENSHOT_PNG = "png"
SCREENSHOT_JPG = "jpg"
SCREENSHOT_SVG = "svg"
DEFAULT_SCREENSHOT_FILETYPE = SCREENSHOT_PNG

LAYOUT_DOT = "dot"
LAYOUT_DAGRE = "dagre"
LAYOUT_FCOSE = "fcose"
DEFAULT_LAYOUT_ALG = LAYOUT_DAGRE

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
    "gc": ("GC %", "number"),
    "gc_content": ("GC %", "number"),
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
    "length": ("Length", "number"),
    "cov": ("Cov.", "number"),
    "color": ("Color", "text"),
    "first_nt": ("First nt", "text"),
    "kmer_cov": ("k-mer cov.", "number"),
}

# some attributes are obvious and/or not worth showing in the selected element
# tables, since there is not a lot of space. Record these here.
NODEATTRS_SKIP = ()
EDGEATTRS_SKIP = (
    # Flye
    "color",
    "dir",
    # LJA
    "label",
    "labeltooltip",
)

# Showing unformatted numbers to the user looks a bit gross -- e.g.
# "12345.123213" might be better shown as "12,345.12" or something. we can use
# column-specific valueFormatters to enable this:
# https://dash.plotly.com/dash-ag-grid/value-formatters
# https://community.plotly.com/t/dash-ag-grid-format-values/72145/2
FMT_THOUSANDS_SEP = {
    "function": "params.value !== null ? params.value.toLocaleString() : null"
}
FMT_PERCENT = {
    "function": "params.value !== null ? (params.value * 100).toFixed(2) + '%' : null"
}
# See https://github.com/marbl/MetagenomeScope/issues/290
FMT_APPROX_LENGTH = {
    "function": "params.value !== null ? (params.value / 1000).toLocaleString() + 'k' : null"
}

NODEATTR2FMT = {
    "length": FMT_THOUSANDS_SEP,
    "depth": FMT_THOUSANDS_SEP,
    "cov": FMT_THOUSANDS_SEP,
    "gc": FMT_PERCENT,
    "gc_content": FMT_PERCENT,
}

EDGEATTR2FMT = {
    "mean": FMT_THOUSANDS_SEP,
    "stdev": FMT_THOUSANDS_SEP,
    "bsize": FMT_THOUSANDS_SEP,
    "multiplicity": FMT_THOUSANDS_SEP,
    "approx_length": FMT_APPROX_LENGTH,
    "cov": FMT_THOUSANDS_SEP,
    "kmer_cov": FMT_THOUSANDS_SEP,
}
