from dash import html

###############################################################################
# Default drawing settings
###############################################################################

# values in the draw settings checklist
SHOW_PATTERNS = "patterns"
DO_LAYOUT_ANIMATION = "animate"
DO_RECURSIVE_LAYOUT = "recursive"
USE_GV_PORTS = "ports"

# by default, which draw settings are enabled?
DEFAULT_SHOW_PATTERNS = True
DEFAULT_DO_LAYOUT_ANIMATION = True
DEFAULT_DO_RECURSIVE_LAYOUT = False
DEFAULT_USE_GV_PORTS = False

DEFAULT_DRAW_SETTINGS = []
if DEFAULT_SHOW_PATTERNS:
    DEFAULT_DRAW_SETTINGS.append(SHOW_PATTERNS)
if DEFAULT_DO_LAYOUT_ANIMATION:
    DEFAULT_DRAW_SETTINGS.append(DO_LAYOUT_ANIMATION)
if DEFAULT_DO_RECURSIVE_LAYOUT:
    DEFAULT_DRAW_SETTINGS.append(DO_RECURSIVE_LAYOUT)
if DEFAULT_USE_GV_PORTS:
    DEFAULT_DRAW_SETTINGS.append(USE_GV_PORTS)

DOT_TEXT = html.Span("dot", style={"font-style": "italic"})

DRAW_SETTINGS_OPTIONS = [
    {
        "label": "Show patterns",
        "value": SHOW_PATTERNS,
    },
    {
        "label": html.Span(
            [
                "Lay out patterns recursively (",
                DOT_TEXT,
                " only)",
            ]
        ),
        "value": DO_RECURSIVE_LAYOUT,
    },
    {
        "label": html.Span(
            [
                "Fix edges' headports and tailports (",
                DOT_TEXT,
                " only)",
            ]
        ),
        "value": USE_GV_PORTS,
    },
    {
        "label": "Animate layout (Dagre & fCoSE only)",
        "value": DO_LAYOUT_ANIMATION,
    },
]

COLORING_RANDOM = "random"
COLORING_UNIFORM = "uniform"
COLORING_GRAPH = "graph"

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
LAYOUT_SFDP = "sfdp"
LAYOUT_DAGRE = "dagre"
LAYOUT_FCOSE = "fcose"
DEFAULT_LAYOUT_ALG = LAYOUT_DOT
LAYOUT2GVPROG = {LAYOUT_DOT: "dot", LAYOUT_SFDP: "sfdp"}
# basically, we don't want to support these settings with sfdp, so encode that
# here
GVLAYOUT2RECURSIVE = {LAYOUT_DOT: True, LAYOUT_SFDP: False}
GVLAYOUT2GV_PORTS = {LAYOUT_DOT: True, LAYOUT_SFDP: False}
GVLAYOUT2RECORD_EDGE_CTRL_PTS = {LAYOUT_DOT: True, LAYOUT_SFDP: False}

###############################################################################
# Coloring UI
###############################################################################

COLORFUL_RANDOM_TEXT = html.Span(
    [
        html.Span(
            "R",
            style={"color": "#e00"},
        ),
        html.Span(
            "a",
            style={"color": "#e70"},
        ),
        html.Span(
            "n",
            style={"color": "#aa8822"},
        ),
        html.Span(
            "d",
            style={"color": "#22aa11"},
        ),
        html.Span(
            "o",
            style={"color": "#0bf"},
        ),
        html.Span(
            "m",
            style={"color": "#d3d"},
        ),
    ]
)

###############################################################################
# Default path settings
###############################################################################

PATH_SETTINGS_ZOOM = "zoom"
PATH_SETTINGS_TOAST = "toast"

PATH_SETTINGS_OPTIONS = [
    {
        "label": "Zoom in on selected paths",
        "value": PATH_SETTINGS_ZOOM,
    },
    {
        "label": "Show selected paths' details",
        "value": PATH_SETTINGS_TOAST,
    },
]

DEFAULT_PATH_SETTINGS = [PATH_SETTINGS_ZOOM, PATH_SETTINGS_TOAST]

###############################################################################
# Lists of options (e.g. for histograms, or for layout parameters)
###############################################################################

OPTIONS_SEP = html.Div(style={"margin-top": "0.3em"})

###############################################################################
# Histograms in the info dialog
###############################################################################

# axis scales (correspond to yaxis_type plotly go.Histogram settings)
SCALE_LINEAR = "linear"
SCALE_LOG = "log"

# should the hist of stuff per cc show nodes or edges?
# (showing them stacked looks gross imo...)
NODES_HIST = "nodes"
EDGES_HIST = "edges"

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

###############################################################################
# General table stuff (both paths and selected nodes/edges/patterns)
###############################################################################
DASH_GRID_OPTIONS = {
    "theme": "legacy",
    # We need to include this, or column names that include periods (e.g.
    # "mult." in Flye output) will completely explode the tables and make me
    # spend like an hour debugging it. https://stackoverflow.com/q/58772051
    # https://dash.plotly.com/dash-ag-grid/column-definitions#suppressing-field-dot-notation
    "suppressFieldDotNotation": True,
}

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
