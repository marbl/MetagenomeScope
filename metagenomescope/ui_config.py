###############################################################################
# Default drawing settings
###############################################################################

# values in the draw settings checklist
SHOW_PATTERNS = "patterns"
DO_LAYOUT_ANIMATION = "animate"
DO_RECURSIVE_LAYOUT = "recursive"

# by default, which draw settings are enabled?
DEFAULT_SHOW_PATTERNS = True
DEFAULT_DO_LAYOUT_ANIMATION = True
DEFAULT_DO_RECURSIVE_LAYOUT = False

DEFAULT_DRAW_SETTINGS = []
if DEFAULT_SHOW_PATTERNS:
    DEFAULT_DRAW_SETTINGS.append(SHOW_PATTERNS)
if DEFAULT_DO_LAYOUT_ANIMATION:
    DEFAULT_DRAW_SETTINGS.append(DO_LAYOUT_ANIMATION)
if DEFAULT_DO_RECURSIVE_LAYOUT:
    DEFAULT_DRAW_SETTINGS.append(DO_RECURSIVE_LAYOUT)

DRAW_SETTINGS_OPTIONS = [
    {
        "label": "Show patterns",
        "value": SHOW_PATTERNS,
    },
    {
        "label": "Lay out patterns recursively (Graphviz only)",
        "value": DO_RECURSIVE_LAYOUT,
    },
    {
        "label": "Animate layout (Dagre & fCoSE only)",
        "value": DO_LAYOUT_ANIMATION,
    },
]

COLORING_RANDOM = "random"
COLORING_UNIFORM = "uniform"

DEFAULT_NODE_COLORING = COLORING_RANDOM
DEFAULT_EDGE_COLORING = COLORING_RANDOM

NODE_LABELS = "nodelbls"
EDGE_LABELS = "edgelbls"
PATTERN_LABELS = "pattlbls"
DEFAULT_LABELS_NODE_CENTRIC = [NODE_LABELS]
DEFAULT_LABELS_EDGE_CENTRIC = [EDGE_LABELS]

SCREENSHOT_PNG = "png"
SCREENSHOT_JPG = "jpg"
SCREENSHOT_SVG = "svg"
DEFAULT_SCREENSHOT_FILETYPE = SCREENSHOT_PNG

LAYOUT_DOT = "dot"
LAYOUT_DAGRE = "dagre"
LAYOUT_FCOSE = "fcose"
DEFAULT_LAYOUT_ALG = LAYOUT_DOT

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
# Tables of selected elements, and other things involving "metadata" like covs
###############################################################################

NODE_TBL_NAME_COL = "N"

EDGE_TBL_SRC_COL = "S"
EDGE_TBL_TGT_COL = "T"

PATT_TBL_ID_COL = "I"
PATT_TBL_TYPE_COL = "T"
PATT_TBL_NCT_COL = "N"
PATT_TBL_ECT_COL = "E"
PATT_TBL_PCT_COL = "P"

FLYE_INFO_COLS_TO_RENAME = {"cov.": "cov"}

# Maps "internal" names for node / edge properties to human-readable names, and
# AG Grid cellDataType parameters.
# (As we add on more filetype parsers, feel free to extend these structures.)
NODEATTR2HRT = {
    "name": ("ID", "text"),
    "length": ("Length", "text"),
    "orientation": ("+/-", "text"),
    "cov": ("Cov.", "number"),
    "circ.": ("Circular?", "text"),
    "repeat": ("Repeat?", "text"),
    # To whoever is reading this: figuring out why column names with periods
    # were breaking the tables took like an hour out of my life. I really hope
    # you appreciate this information about multiplicity, because I sold a part
    # of my soul in order to make it viewable
    "mult.": ("Mult.", "number"),
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
    "mean": ("\u03bc", "number"),
    "stdev": ("\u03c3", "number"),
    "orientation": ("Orient.", "text"),
    "bsize": ("bsize", "number"),
    "multiplicity": ("Multiplicity", "number"),
    "id": ("ID", "text"),
    "approx_length": ("~Length", "number"),
    "length": ("Length", "number"),
    "cov": ("Cov.", "number"),
    "color": ("Color", "text"),
    "first_nt": ("First nt", "text"),
    "kp1mer_cov": ("(K+1)-mer cov.", "number"),
    "containment": ("Containment?", "text"),
}

COVATTR2SINGLE = {
    "cov": "coverage",
    "kp1mer_cov": "(K+1)-mer coverage",
    "bsize": "bundle size",
    "multiplicity": "multiplicity",
}

COVATTR2PLURAL = {
    "cov": "coverages",
    "kp1mer_cov": "(K+1)-mer coverages",
    "bsize": "bundle sizes",
    "multiplicity": "multiplicities",
}

COVATTR2TITLE = {
    "cov": "Coverage",
    "kp1mer_cov": "(K+1)-mer Coverage",
    "bsize": "Bundle Size",
    "multiplicity": "Multiplicity",
}

# some attributes are obvious and/or not worth showing in the selected element
# tables, since there is not a lot of space. Record these here.
NODEATTRS_SKIP = (
    # Flye (... at least in my opinion. like you're already looking at the
    # graph right?)
    "circ.",
)
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
    "cov": FMT_THOUSANDS_SEP,
    "gc": FMT_PERCENT,
    "mult.": FMT_THOUSANDS_SEP,
    "gc_content": FMT_PERCENT,
}

EDGEATTR2FMT = {
    "mean": FMT_THOUSANDS_SEP,
    "stdev": FMT_THOUSANDS_SEP,
    "bsize": FMT_THOUSANDS_SEP,
    "multiplicity": FMT_THOUSANDS_SEP,
    "length": FMT_THOUSANDS_SEP,
    "approx_length": FMT_APPROX_LENGTH,
    "cov": FMT_THOUSANDS_SEP,
    "kp1mer_cov": FMT_THOUSANDS_SEP,
}
