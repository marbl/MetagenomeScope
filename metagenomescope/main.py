#!/usr/bin/env python3

import logging
import math
import dash
import dash_cytoscape as cyto
import plotly.graph_objects as go
from collections import defaultdict
from dash import (
    html,
    callback,
    clientside_callback,
    ctx,
    dcc,
    Input,
    Output,
    State,
)
from . import defaults, css_config, ui_config, ui_utils, cy_utils
from .log_utils import start_log, log_lines_with_sep
from .misc_utils import pluralize
from .graph import AssemblyGraph, graph_utils
from .errors import UIError, WeirdError

# Needed for layout extensions. Probably comment this out when we get
# actual Graphviz layouts back in (or maybe keep this in if people want
# to try out fcose / dagre / etc)
cyto.load_extra_layouts()


def run(
    graph: str = None,
    verbose: bool = defaults.VERBOSE,
):
    """Reads the graph and starts a Dash app for visualizing it.

    Parameters
    ----------
    graph: str
        Path to the assembly graph to be visualized.

    verbose: bool
        If True, include DEBUG messages in the log output.

    Returns
    -------
    None
    """
    start_log(verbose)
    logger = logging.getLogger(__name__)
    log_lines_with_sep(
        [
            "Settings:",
            f"Graph: {graph}",
            f"Verbose?: {verbose}",
        ],
        logger.info,
        endsepline=True,
    )

    # Read the assembly graph file and create an object representing it.
    # Creating the AssemblyGraph object will identify patterns, scale nodes and
    # edges, etc.
    ag = AssemblyGraph(graph)

    # Prepare some of the UI components in advance. A nice thing about Dash
    # (which I guess comes from it being built on top of React) is that we can
    # define these kinds of components and reuse them without having to rewrite
    # a bunch of code.
    ctrl_sep = html.Div(
        style={
            "width": "100%",
            "height": css_config.CONTROLS_BORDER_THICKNESS,
            "background-color": "#002",
            "margin": "1.25em 0",
        },
        className="ctrlSep",
    )

    ctrl_sep_invis = html.Div(
        style={
            "width": "100%",
            "height": "0",
            "background-color": "#002",
            "margin": "0.7em 0",
        },
        className="ctrlSep",
    )

    # If there are multiple components, show a "Components" tab in the info
    # dialog with information about these components. Also show various options
    # for selecting which component(s) to draw.
    #
    # This is all useless and confusing if the graph only has one component, so
    # this flag lets us figure out if we should show or hide this kinda stuff
    multiple_ccs = len(ag.components) > 1

    # Options for drawing components
    # If there is only one cc in the graph, we'll disable the "one component"
    # options. We'll make the "all components" option the default, and rename
    # it to be clearer. (Um, we could also change its icon from an asterisk to
    # something else if desired, but I actually think keeping the asterisk
    # makes sense. This way people don't worry that they are somehow seeing
    # "less" of the graph than they would otherwise. Like this is still the
    # "draw everything" option, if that makes sense.)
    cc_selection_options = {
        "ccDrawingSizeRank": [
            html.I(className="bi bi-hash"),
            html.Span(
                "One component (by size rank)",
            ),
        ],
        "ccDrawingNodeName": [
            html.I(className="bi bi-search"),
            html.Span(
                "One component (with a node)",
            ),
        ],
        "ccDrawingAll": [
            html.I(className="bi bi-asterisk"),
            html.Span(
                (
                    "All components"
                    if multiple_ccs
                    else "Only component in the graph"
                ),
            ),
        ],
    }
    DEFAULT_CC_SELECTION_METHOD = (
        "ccDrawingSizeRank" if multiple_ccs else "ccDrawingAll"
    )
    CC_SELECTION_A_CLASSES_MULTIPLE_CCS = "dropdown-item"
    CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {}
    if not multiple_ccs:
        # https://getbootstrap.com/docs/5.3/components/dropdowns/#disabled
        # thankfully this seems to prevent dash from noticing click events on
        # the disabled <a>s in question :)
        CC_SELECTION_A_CLASSES_MULTIPLE_CCS += " disabled"
        CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {"aria-disabled": "true"}

    # update_title=None prevents Dash's default "Updating..." page title change
    app = dash.Dash(__name__, title="MgSc", update_title=None)
    CONTROLS_TOGGLER_ICON_CLASSES = "bi bi-list"
    app.layout = html.Div(
        [
            # controls toggler (hamburger button)
            html.Div(
                html.I(
                    id="controlsTogglerIcon",
                    className=CONTROLS_TOGGLER_ICON_CLASSES,
                ),
                id="controlsToggler",
            ),
            # controls
            html.Div(
                [
                    html.H4(
                        ag.basename,
                        className="font-monospace",
                        style={
                            "margin-top": "2em",
                            # If the user passes in a graph with a really
                            # long filename, split it over multiple lines.
                            # There are multiple ways to do this in CSS but
                            # this seems best for this purpose:
                            # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_text/Wrapping_breaking_text
                            "word-break": "break-all",
                        },
                    ),
                    html.P(
                        [
                            f"{pluralize(ag.node_ct, 'node')}, "
                            f"{pluralize(ag.edge_ct, 'edge')}."
                        ]
                    ),
                    html.P([f"{pluralize(len(ag.components), 'component')}."]),
                    ctrl_sep_invis,
                    html.P(
                        [
                            html.Button(
                                [
                                    html.I(className="bi bi-grid-1x2-fill"),
                                    html.Span(
                                        "Graph info", className="iconlbl"
                                    ),
                                ],
                                id="infoButton",
                                className="btn btn-light",
                                type="button",
                                **{
                                    "data-bs-toggle": "modal",
                                    "data-bs-target": "#infoDialog",
                                },
                            )
                        ],
                    ),
                    ctrl_sep,
                    html.H4("Draw"),
                    # https://getbootstrap.com/docs/5.3/components/dropdowns/#single-button
                    html.Div(
                        [
                            html.Button(
                                cc_selection_options[
                                    DEFAULT_CC_SELECTION_METHOD
                                ],
                                className="btn btn-sm btn-light dropdown-toggle",
                                id="ccDrawingSelect",
                                type="button",
                                style={"width": "100%"},
                                # We'll update the button's value along with its
                                # children when the user selects a drawing method.
                                # The value is used by our code to determine the
                                # currently-selected drawing method.
                                value=DEFAULT_CC_SELECTION_METHOD,
                                **{
                                    "data-bs-toggle": "dropdown",
                                    "aria-expanded": "false",
                                },
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        html.A(
                                            cc_selection_options[
                                                "ccDrawingSizeRank"
                                            ],
                                            className=CC_SELECTION_A_CLASSES_MULTIPLE_CCS,
                                            id="ccDrawingSizeRank",
                                            **CC_SELECTION_A_ATTRS_MULTIPLE_CCS,
                                        ),
                                    ),
                                    html.Li(
                                        html.A(
                                            cc_selection_options[
                                                "ccDrawingNodeName"
                                            ],
                                            className=CC_SELECTION_A_CLASSES_MULTIPLE_CCS,
                                            id="ccDrawingNodeName",
                                            **CC_SELECTION_A_ATTRS_MULTIPLE_CCS,
                                        ),
                                    ),
                                    html.Li(
                                        html.A(
                                            cc_selection_options[
                                                "ccDrawingAll"
                                            ],
                                            className="dropdown-item",
                                            id="ccDrawingAll",
                                        ),
                                    ),
                                ],
                                id="ccDrawingUl",
                                className="dropdown-menu dropdown-menu-sm",
                                style={"font-size": "0.85em"},
                            ),
                        ],
                        className="dropdown",
                    ),
                    html.Div(
                        [
                            html.Button(
                                html.I(className="bi bi-dash-lg"),
                                id="ccSizeRankDecrBtn",
                                # might add borders to the sides of these later
                                className="btn btn-light cc-size-rank-adj",
                                type="button",
                            ),
                            # dash doesn't have a html.Input thing like it
                            # does for other HTML tags, so we use dcc.Input
                            # which apparently is close enough
                            # (https://github.com/plotly/dash/issues/2791)
                            dcc.Input(
                                type="number",
                                id="ccSizeRankSelector",
                                className="form-control",
                                value=1,
                                min=1,
                                max=len(ag.components),
                            ),
                            html.Button(
                                html.I(className="bi bi-plus-lg"),
                                id="ccSizeRankIncrBtn",
                                className="btn btn-light cc-size-rank-adj",
                                type="button",
                            ),
                        ],
                        id="ccSizeRankSelectorEles",
                        className=css_config.CC_SELECTOR_ELES_CLASSES
                        + (
                            " hidden"
                            if "ccDrawingSizeRank"
                            != DEFAULT_CC_SELECTION_METHOD
                            else ""
                        ),
                    ),
                    html.Div(
                        [
                            dcc.Input(
                                type="text",
                                id="ccNodeNameSelector",
                                className="form-control",
                                placeholder="Node name",
                            ),
                        ],
                        id="ccNodeNameSelectorEles",
                        className=css_config.CC_SELECTOR_ELES_CLASSES
                        + (
                            " hidden"
                            if "ccDrawingNodeName"
                            != DEFAULT_CC_SELECTION_METHOD
                            else ""
                        ),
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                options=[
                                    {
                                        "label": "Show patterns",
                                        "value": ui_config.SHOW_PATTERNS,
                                    },
                                ],
                                value=ui_config.DEFAULT_DRAW_SETTINGS,
                                id="drawSettingsChecklist",
                            )
                        ],
                        className="form-check",
                    ),
                    html.Button(
                        [
                            html.I(className="bi bi-brush-fill"),
                            html.Span(
                                "Draw",
                                className="iconlbl",
                            ),
                        ],
                        id="drawButton",
                        className="btn btn-light drawCtrl",
                        type="button",
                    ),
                    ctrl_sep,
                    html.H4(
                        "Colors",
                    ),
                    ctrl_sep_invis,
                    html.H5(
                        "Nodes",
                    ),
                    html.Div(
                        [
                            dcc.RadioItems(
                                options=[
                                    {
                                        "label": "Random",
                                        "value": ui_config.COLORING_RANDOM,
                                    },
                                    {
                                        "label": "Uniform",
                                        "value": ui_config.COLORING_UNIFORM,
                                    },
                                ],
                                value=ui_config.DEFAULT_NODE_COLORING,
                                inline=True,
                                id="nodeColorRadio",
                            ),
                        ],
                        className="form-check",
                    ),
                    ctrl_sep_invis,
                    html.H5(
                        "Edges",
                    ),
                    html.Div(
                        [
                            dcc.RadioItems(
                                options=[
                                    {
                                        "label": "Random",
                                        "value": ui_config.COLORING_RANDOM,
                                    },
                                    {
                                        "label": "Uniform",
                                        "value": ui_config.COLORING_UNIFORM,
                                    },
                                ],
                                value=ui_config.DEFAULT_EDGE_COLORING,
                                inline=True,
                                id="edgeColorRadio",
                            ),
                        ],
                        className="form-check",
                    ),
                    ctrl_sep,
                    # html.H4("Selected"),
                ],
                id="controls",
                style={
                    "position": "absolute",
                    "top": "0em",
                    "bottom": "0em",
                    "left": "0em",
                    "width": css_config.CONTROLS_WIDTH,
                    "text-align": "center",
                    # only show the scrollbar when needed - firefox doesn't
                    # seem to need this, but chrome does
                    "overflow-y": "auto",
                    "z-index": "1",
                    "background-color": "#123",
                    "color": "#ccc",
                    "border-right": f"{css_config.CONTROLS_BORDER_THICKNESS} solid #002",
                    "transition": f"left {css_config.CONTROLS_TRANSITION_DURATION}",
                },
                className="",
            ),
            # cy
            html.Div(
                [
                    # In previous versions of MetagenomeScope, we would destroy
                    # and create a Cytoscape.js instance every time the user
                    # would draw a new section of the graph. Here, though, it
                    # is more natural to have a single persistent instance of
                    # Cytoscape.js -- and just add elements, adjust its
                    # stylesheet, etc. as requested. This both works better
                    # with Dash and is recommended by Cytoscape.js' docs
                    # ("Optimisations" > "Recycle large instances").
                    cyto.Cytoscape(
                        id="cy",
                        elements=[],
                        layout={"name": "dagre", "rankDir": "LR"},
                        style={
                            "width": "100%",
                            "height": "100%",
                        },
                        boxSelectionEnabled=True,
                        maxZoom=9,
                        stylesheet=cy_utils.get_cyjs_stylesheet(
                            node_coloring=ui_config.DEFAULT_NODE_COLORING,
                            edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
                        ),
                    )
                ],
                id="cyDiv",
                style={
                    "position": "absolute",
                    "left": css_config.CONTROLS_WIDTH,
                    "top": "0em",
                    "bottom": "0em",
                    "right": "0em",
                    "z-index": "0",
                    # for debugging layout jank...
                    # "border": "3px solid #00ff00",
                    # NOTE: so, if you adjust this
                    # (like https://js.cytoscape.org/demos/fcose-gene/) so that
                    # the control panel is on the right and we're changing the
                    # "right" style property of #cyDiv, then the canvas
                    # contents no longer shift (while still resizing the
                    # canvas to fill the void left by the hidden control
                    # panel). I spent multiple hours trying to find a way
                    # to make this work on the left side of the canvas and was
                    # unsuccessful -- I think it might be something to do with
                    # how HTML canvases work under the hood. idk. anyway this
                    # at least adds a smooth transition.
                    "transition": f"left {css_config.CONTROLS_TRANSITION_DURATION}",
                },
            ),
            # Graph info modal dialog
            # https://getbootstrap.com/docs/5.3/components/modal/#live-demo
            html.Div(
                html.Div(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H1(
                                        [
                                            html.I(
                                                className="bi bi-grid-1x2-fill"
                                            ),
                                            html.Span(
                                                "Graph information",
                                                className="iconlbl",
                                            ),
                                        ],
                                        className="modal-title fs-5",
                                        id="infoDialogLabel",
                                    ),
                                    html.Button(
                                        className="btn-close",
                                        type="button",
                                        **{
                                            "data-bs-dismiss": "modal",
                                            "aria-label": "Close",
                                        },
                                    ),
                                ],
                                className="modal-header",
                            ),
                            html.Div(
                                [
                                    # navigation adapted from
                                    # https://getbootstrap.com/docs/5.3/components/navs-tabs/#javascript-behavior
                                    html.Ul(
                                        [
                                            html.Li(
                                                html.Button(
                                                    "Overview",
                                                    className="nav-link active",
                                                    id="statsTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#statsTabPane",
                                                        "aria-controls": "statsTabPane",
                                                        "aria-selected": "true",
                                                    },
                                                ),
                                                className="nav-item",
                                                role="presentation",
                                            ),
                                            (
                                                html.Li(
                                                    html.Button(
                                                        "Components",
                                                        className="nav-link",
                                                        id="ccTab",
                                                        type="button",
                                                        role="tab",
                                                        **{
                                                            "data-bs-toggle": "tab",
                                                            "data-bs-target": "#ccTabPane",
                                                            "aria-controls": "ccTabPane",
                                                            "aria-selected": "false",
                                                        },
                                                    ),
                                                    className="nav-item",
                                                    role="presentation",
                                                )
                                                if multiple_ccs
                                                else None
                                            ),
                                            html.Li(
                                                html.Button(
                                                    "Sequences",
                                                    className="nav-link",
                                                    id="seqLenTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#seqLenTabPane",
                                                        "aria-controls": "seqLenTabPane",
                                                        "aria-selected": "false",
                                                    },
                                                ),
                                                className="nav-item",
                                                role="presentation",
                                            ),
                                        ],
                                        id="infoDialogTabs",
                                        role="tablist",
                                        className="nav nav-tabs",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Table(
                                                        html.Tbody(
                                                            [
                                                                html.Tr(
                                                                    [
                                                                        html.Th(
                                                                            "Filename"
                                                                        ),
                                                                        html.Th(
                                                                            "Filetype",
                                                                        ),
                                                                        html.Th(
                                                                            "# nodes"
                                                                        ),
                                                                        html.Th(
                                                                            "# edges"
                                                                        ),
                                                                        html.Th(
                                                                            "# components"
                                                                        ),
                                                                    ]
                                                                ),
                                                                html.Tr(
                                                                    [
                                                                        html.Td(
                                                                            ag.basename,
                                                                            className="font-monospace",
                                                                        ),
                                                                        html.Td(
                                                                            ag.filetype,
                                                                            className="font-monospace",
                                                                        ),
                                                                        html.Td(
                                                                            f"{ag.node_ct:,}",
                                                                        ),
                                                                        html.Td(
                                                                            f"{ag.edge_ct:,}",
                                                                        ),
                                                                        html.Td(
                                                                            f"{len(ag.components):,}"
                                                                        ),
                                                                    ]
                                                                ),
                                                            ]
                                                        ),
                                                        className=css_config.INFO_DIALOG_TABLE_CLASSES,
                                                    ),
                                                    html.P(
                                                        "Note that, as of writing, these counts include "
                                                        "both + and - copies of nodes / edges / components."
                                                    ),
                                                    html.P(
                                                        [
                                                            "Based on the input graph's filetype, we "
                                                            "assume its sequences are stored on its ",
                                                            html.Span(
                                                                ag.seq_noun
                                                                + "s",
                                                                className="fw-bold",
                                                            ),
                                                            ".",
                                                        ]
                                                    ),
                                                    ui_utils.get_length_info(
                                                        ag
                                                    ),
                                                ],
                                                id="statsTabPane",
                                                className="tab-pane fade show active",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "statsTab"
                                                },
                                            ),
                                            (
                                                html.Div(
                                                    [
                                                        html.Ul(
                                                            [
                                                                html.Li(
                                                                    html.Button(
                                                                        "Treemap of nodes",
                                                                        className="nav-link active",
                                                                        id="ccNestTreemapTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestTreemapTabPane",
                                                                            "aria-controls": "ccNestTreemapTabPane",
                                                                            "aria-selected": "true",
                                                                        },
                                                                    ),
                                                                    className="nav-item",
                                                                    role="presentation",
                                                                ),
                                                                html.Li(
                                                                    html.Button(
                                                                        "Histogram of nodes/edges",
                                                                        className="nav-link",
                                                                        id="ccNestHistTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestHistTabPane",
                                                                            "aria-controls": "ccNestHistTabPane",
                                                                            "aria-selected": "false",
                                                                        },
                                                                    ),
                                                                    className="nav-item",
                                                                    role="presentation",
                                                                ),
                                                            ],
                                                            className="nav nav-tabs",
                                                            id="ccTabs",
                                                            role="tablist",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Div(
                                                                    html.Div(
                                                                        id="ccTreemapContainer",
                                                                    ),
                                                                    className="tab-pane fade show active",
                                                                    id="ccNestTreemapTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestTreemapTab"
                                                                    },
                                                                ),
                                                                html.Div(
                                                                    html.Div(
                                                                        id="ccHistContainer",
                                                                    ),
                                                                    className="tab-pane fade",
                                                                    id="ccNestHistTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestHistTab"
                                                                    },
                                                                ),
                                                            ],
                                                            className="tab-content",
                                                            id="ccNestTabContent",
                                                        ),
                                                    ],
                                                    id="ccTabPane",
                                                    className="tab-pane fade show",
                                                    role="tabpanel",
                                                    tabIndex="0",
                                                    **{
                                                        "aria-labelledby": "ccTab"
                                                    },
                                                )
                                                if multiple_ccs
                                                else None
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        id="seqLenHistContainer",
                                                    ),
                                                ],
                                                id="seqLenTabPane",
                                                className="tab-pane fade",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "seqLenTab"
                                                },
                                            ),
                                        ],
                                        className="tab-content",
                                        id="infoDialogTabContent",
                                    ),
                                ],
                                className="modal-body",
                            ),
                        ],
                        className="modal-content",
                    ),
                    className="modal-dialog modal-xl",
                ),
                id="infoDialog",
                className="modal fade",
                # additional accessibility things from bootstrap examples that
                # may not be necessary for a visualization tool like this atm
                **{
                    "aria-hidden": "true",
                    "aria-labelledby": "infoDialogLabel",
                    "tabIndex": "-1",
                },
            ),
            # toast messages will go here. you can change top-0 to bottom-0 to
            # position these in the bottom right of the window; see
            # https://getbootstrap.com/docs/5.3/components/toasts/#live-example
            html.Div(
                id="toastHolder",
                className="toast-container position-fixed top-0 end-0 p-3",
            ),
            # we'll update this when it's time to draw the graph -- after
            # we flush it (removing all currently present elements) and
            # before we redraw it (based on updating this data).
            # See https://github.com/plotly/dash-cytoscape/issues/106#issuecomment-3535358135
            dcc.Store(
                id="doneFlushing",
            ),
        ],
    )

    if multiple_ccs:

        @callback(
            Output("ccHistContainer", "children"),
            Input("ccNestHistTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_hist(n_clicks):
            graph_utils.validate_multiple_ccs(ag)
            cc_node_cts, cc_edge_cts = ag.get_component_node_and_edge_cts()

            fig = go.Figure()
            fig.add_trace(
                go.Histogram(
                    x=cc_node_cts,
                    marker_color="#0a0",
                    marker_line_width=2,
                    marker_line_color="#030",
                    name="# nodes",
                )
            )
            fig.add_trace(
                go.Histogram(
                    x=cc_edge_cts,
                    marker_color="#447",
                    marker_line_width=2,
                    marker_line_color="#005",
                    marker_pattern_shape="x",
                    marker_pattern_fgcolor="#fff",
                    name="# edges",
                )
            )
            fig.update_layout(
                barmode="stack",
                title_text="Numbers of nodes and edges per component",
                xaxis_title_text="# nodes or # edges",
                yaxis_title_text="# components",
                font=dict(size=16),
                # By default the title is shoved up really high above
                # the figure; this repositions it to be closer, while
                # still keeping a bit of padding. From
                # https://community.plotly.com/t/margins-around-graphs/11550/6
                title=dict(yanchor="bottom", y=1, yref="paper"),
                title_pad=dict(b=30),
                margin=dict(t=75),
            )
            # Hack to add padding to the right of the y-axis tick labels:
            # https://stackoverflow.com/a/66736119
            fig.update_yaxes(ticksuffix=" ")
            return dcc.Graph(figure=fig)

        @callback(
            Output("ccTreemapContainer", "children"),
            Input("ccTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_treemap(n_clicks):
            graph_utils.validate_multiple_ccs(ag)
            cc_names = ["Components"]
            cc_sizes = [ag.node_ct]
            cc_parents = [""]
            if len(ag.components) >= ui_config.MIN_LARGE_CC_COUNT:
                node_ct2cc_nums = defaultdict(list)
                for cc in ag.components:
                    node_ct2cc_nums[cc.num_full_nodes].append(cc.cc_num)
                for node_ct, cc_nums in node_ct2cc_nums.items():
                    cc_ct = len(cc_nums)
                    if cc_ct >= ui_config.MIN_SAME_SIZE_CC_COUNT:
                        # Enough ccs have the same exact amount of nodes that
                        # we should collapse them in the treemap
                        min_cc_num = min(cc_nums)
                        max_cc_num = max(cc_nums)
                        if max_cc_num - min_cc_num + 1 != len(cc_nums):
                            raise WeirdError(
                                "Something weird is up with the size ranks? "
                                f"|{min_cc_num:,} to {max_cc_num:,}| != "
                                f"{len(cc_nums):,}"
                            )
                        cc_names.append(
                            f"#{min_cc_num:,} - #{max_cc_num:,} "
                            f"({node_ct:,}-node components)"
                        )
                        # If we have let's say 5 components that each contain
                        # exactly 3 nodes, then they represent 15 nodes total.
                        cc_sizes.append(node_ct * cc_ct)
                        cc_parents.append("Components")
                    else:
                        for cc_num in cc_nums:
                            cc_names.append(f"#{cc_num:,}")
                            cc_sizes.append(node_ct)
                            cc_parents.append("Components")
            else:
                for cc in ag.components:
                    cc_names.append(f"#{cc.cc_num:,}")
                    cc_sizes.append(cc.num_full_nodes)
                    cc_parents.append("Components")
            fig = go.Figure(
                go.Treemap(
                    labels=cc_names,
                    parents=cc_parents,
                    values=cc_sizes,
                    # Need to set "total" here so that the size of the top-
                    # level element is treated as the sum of its children,
                    # rather than as an extra size in addition to the sum
                    # of its children. (And we want to set a size of the
                    # top-level element in order to show that in the
                    # hover template, etc.)
                    branchvalues="total",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "<b>Nodes:</b> %{value:,} (%{percentRoot:.2%})"
                    ),
                    # If we don't set name="", then the hover popup shows
                    # "trace 0" next to it and that looks gross
                    name="",
                    root_color="#ddd",
                )
            )
            fig.update_layout(
                title_text="Number of nodes per component",
                title=dict(yanchor="bottom", y=1, yref="paper"),
                font=dict(size=16),
                title_pad=dict(b=30),
                margin=dict(l=0, r=0, b=0, t=75),
                # This will hide too-small labels (yay!), at the cost of
                # forcing all other labels to consistently be the same
                # size and disabling transition animations when you
                # like click to expand a box or something (???). Let's
                # see if we can do without it for now.
                # uniformtext=dict(
                #     minsize=12,
                #     mode="show",
                # )
            )
            return dcc.Graph(figure=fig)

    @callback(
        Output("seqLenHistContainer", "children"),
        Input("seqLenTab", "n_clicks"),
        prevent_initial_call=True,
    )
    def plot_seqlen_hist(n_clicks):
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=ag.seq_lengths,
                marker_color="#811",
                marker_line_width=2,
                marker_line_color="#100",
                name="Sequence lengths",
            )
        )
        fig.update_layout(
            title_text=f"{ag.seq_noun.title()} sequence lengths",
            xaxis_title_text="Length (bp)",
            yaxis_title_text=f"# {ag.seq_noun}s",
            font=dict(size=16),
            title=dict(yanchor="bottom", y=1, yref="paper"),
            title_pad=dict(b=30),
            margin=dict(t=75),
        )
        fig.update_yaxes(ticksuffix=" ")
        return dcc.Graph(figure=fig)

    @callback(
        Output("controls", "className"),
        Output("controlsTogglerIcon", "className"),
        Output("cyDiv", "style"),
        State("controls", "className"),
        State("cyDiv", "style"),
        Input("controlsToggler", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_controls(controls_classes, cy_div_style, n_clicks):
        """Toggles visibility of the control panel's div.

        Also toggles the color of the toggler hamburger icon -- it is colored
        light when the controls are visible, and dark when the controls are not
        visible. (We may want to adjust this in a fancier way if/when the user
        can control the background color of the graph, but it's ok for now.)
        """
        if "offscreen-controls" in controls_classes:
            # Make the control panel visible again, and make the cytoscape.js
            # div occupy only part of the screen
            cy_div_style["left"] = css_config.CONTROLS_WIDTH
            return ("", CONTROLS_TOGGLER_ICON_CLASSES, cy_div_style)
        else:
            # Hide the control panel, and make the cytoscape.js div occupy the
            # whole screen
            cy_div_style["left"] = "0em"
            return (
                "offscreen-controls",
                CONTROLS_TOGGLER_ICON_CLASSES + " darkToggler",
                cy_div_style,
            )

    # By default, bootstrap's dropdowns don't change the button element (i.e.
    # the thing showing the name of the dropdown), as an ordinary HTML <select>
    # would. You can use <select>s with bootstrap, but the styling is limited
    # and you can't (easily?) show icons :( You can also use Dash's
    # dcc.Dropdown objects, which DO allow icons and also allow mutating the
    # dropdown name on selecting something, but bootstrap's styling apparently
    # clobbers Dash's and the result looks kind of gross.
    #
    # So! A reasonable option, I think, is using Bootstrap icons but just
    # adding some custom code here to change the dropdown's button based on
    # what gets selected. The "children" output changes the contents of the
    # dropdown button to use the fancy icon and label, and the "value" is an
    # easy-to-read label for what drawing method is currently selected.
    @callback(
        Output("ccDrawingSelect", "children"),
        Output("ccDrawingSelect", "value"),
        Output("ccSizeRankSelectorEles", "className"),
        Output("ccNodeNameSelectorEles", "className"),
        State("ccSizeRankSelectorEles", "className"),
        State("ccNodeNameSelectorEles", "className"),
        Input("ccDrawingSizeRank", "n_clicks"),
        Input("ccDrawingNodeName", "n_clicks"),
        Input("ccDrawingAll", "n_clicks"),
        prevent_initial_call=True,
    )
    def change_drawing_method(
        cc_sr_eles_classes,
        cc_nn_eles_classes,
        cc_sr_clicks,
        cc_nn_clicks,
        cc_all_clicks,
    ):
        if ctx.triggered_id == "ccDrawingSizeRank":
            cc_sr_eles_classes = css_config.CC_SELECTOR_ELES_CLASSES
            cc_nn_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
        elif ctx.triggered_id == "ccDrawingNodeName":
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
            cc_nn_eles_classes = css_config.CC_SELECTOR_ELES_CLASSES
        else:
            # draw all components, so hide both size rank and node name eles
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
            cc_nn_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
        return (
            cc_selection_options[ctx.triggered_id],
            ctx.triggered_id,
            cc_sr_eles_classes,
            cc_nn_eles_classes,
        )

    @callback(
        Output("ccSizeRankSelector", "value"),
        State("ccSizeRankSelector", "value"),
        Input("ccSizeRankDecrBtn", "n_clicks"),
        Input("ccSizeRankIncrBtn", "n_clicks"),
        prevent_initial_call=True,
        allow_duplicate=True,
    )
    def update_cc_size_rank(size_rank, decr_n_clicks, incr_n_clicks):
        if size_rank is None:
            return 1
        if ctx.triggered_id == "ccSizeRankDecrBtn":
            if type(size_rank) is not int:
                return max(math.floor(size_rank), 1)
            if size_rank <= 1:
                return 1
            elif size_rank > len(ag.components):
                return len(ag.components)
            else:
                return size_rank - 1
        else:
            if type(size_rank) is not int:
                return min(math.ceil(size_rank), len(ag.components))
            if size_rank < 1:
                return 1
            elif size_rank >= len(ag.components):
                return len(ag.components)
            else:
                return size_rank + 1

    @callback(
        Output("cy", "stylesheet"),
        Input("nodeColorRadio", "value"),
        Input("edgeColorRadio", "value"),
        prevent_initial_call=True,
        allow_duplicate=True,
    )
    def update_colorings(node_color_radio, edge_color_radio):
        return cy_utils.get_cyjs_stylesheet(
            node_coloring=node_color_radio,
            edge_coloring=edge_color_radio,
        )

    @callback(
        Output("toastHolder", "children"),
        Output("cy", "elements", allow_duplicate=True),
        Output("doneFlushing", "data"),
        State("toastHolder", "children"),
        State("cy", "elements"),
        State("doneFlushing", "data"),
        State("ccDrawingSelect", "value"),
        State("ccSizeRankSelector", "value"),
        State("ccNodeNameSelector", "value"),
        State("drawSettingsChecklist", "value"),
        Input("drawButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def flush(
        curr_toasts,
        curr_cy_eles,
        curr_done_flushing,
        cc_drawing_selection_type,
        size_rank,
        node_name,
        draw_settings,
        draw_btn_n_clicks,
    ):
        logging.debug(
            "Received request to draw the graph. Validating request."
        )

        cc_selection_params = {}

        if cc_drawing_selection_type == "ccDrawingSizeRank":
            # Invalid numbers (with respect to any set min / max values) will
            # be passed here as None, which is nice but does make it tough to
            # distinguish btwn "the <input> is empty" and "the user entered a
            # bad number". Anyway we just handle both cases with the same
            # message.
            #
            # (Note that floats may end up here, because I deliberately did not
            # set step=1 on the size rank selector. This allows the -/+ buttons
            # to actually see the current value and do intelligent rounding in
            # the update_cc_size_rank() callback.)
            if type(size_rank) is not int:
                return (
                    ui_utils.add_error_toast(
                        curr_toasts,
                        "Draw Error",
                        ui_utils.get_cc_size_rank_error_msg(ag),
                    ),
                    curr_cy_eles,
                    {"requestGood": False},
                )
            cc_selection_params = {"cc_size_rank": size_rank}

        elif cc_drawing_selection_type == "ccDrawingNodeName":
            # looks like not typing in the node name field at all results
            # in node_name being None. However, if we type something in and
            # then fully delete it, then node_name becomes "". Eesh!
            if node_name is None or node_name == "":
                return (
                    ui_utils.add_error_toast(
                        curr_toasts, "Draw Error", "No node name specified."
                    ),
                    curr_cy_eles,
                    {"requestGood": False},
                )
            cc_selection_params = {"cc_node_name": node_name}

        # if something goes wrong during drawing, propagate the result to
        # a toast message in the browser without changing the cytoscape div
        try:
            cc_nums = ag.select_cc_nums(**cc_selection_params)
        except UIError as err:
            return (
                ui_utils.add_error_toast(curr_toasts, "Draw Error", str(err)),
                curr_cy_eles,
                {"requestGood": False},
            )

        # Parse other (less easy to mess up) drawing options
        incl_patterns = False
        for val in draw_settings:
            if val == ui_config.SHOW_PATTERNS:
                incl_patterns = True

        # Okay, now we've done enough checks that this request to draw the
        # graph seems good. Let's clear all elements in the graph and trigger
        # draw(), which will actually add new elements to the graph.
        logging.debug("Drawing request seems good. Flushing the graph.")

        return (
            curr_toasts,
            [],
            {
                "requestGood": True,
                "cc_nums": cc_nums,
                "patterns": incl_patterns,
            },
        )

    @callback(
        Output("cy", "elements", allow_duplicate=True),
        State("cy", "elements"),
        Input("doneFlushing", "data"),
        prevent_initial_call=True,
    )
    def draw(curr_cy_eles, curr_done_flushing):
        # as far as I can tell, this gets triggered whenever doneFlushing is
        # updated -- even if it is updated to the exact same thing as it was
        # before. To avoid making us redraw the entire graph if the user just
        # like specified a node name that didn't exist when searching for a cc,
        # we use the "requestGood" key in doneFlushing to let us know when we
        # ACTUALLY want to redraw the graph.
        if curr_done_flushing["requestGood"]:
            logging.debug(
                "Request good, so flushing should be done. Beginning drawing."
            )
            cc_nums = curr_done_flushing["cc_nums"]
            incl_patterns = curr_done_flushing["patterns"]
            logging.debug(
                "Converting graph to Cytoscape.js elements ("
                f"{pluralize(len(cc_nums), 'cc')}, "
                f"show patterns = {incl_patterns}"
                ")..."
            )
            new_cy_eles = ag.to_cyjs(cc_nums, incl_patterns=incl_patterns)
            logging.debug(f"...Done. {len(new_cy_eles):,} ele(s) total.")
            return new_cy_eles
        else:
            logging.debug("Caught a bad drawing request. Not redrawing.")
            return curr_cy_eles

    # It looks like Bootstrap requires us to use JS to show the toast. If we
    # try to show it ourselves (by just adding the "show" class when creating
    # the toast) then the toast never goes away and also doesn't have smooth
    # animation when appearing. As far as I can tell, using a clientside
    # callback (https://dash.plotly.com/clientside-callbacks) is the smoothest
    # way to do this.
    #
    # (The "data-mgsc-shown" attribute makes sure that we don't re-show a toast
    # that has already been shown. This is because one of the draw() callback's
    # outputs is the toastHolder's children, so even if we just draw the graph
    # successfully without triggering any new toasts then this clientside
    # callback will still be triggered. Oh no! "data-mgsc-shown" fixes things.)
    clientside_callback(
        """
        function(toasts) {
            var tele = document.getElementById("toastHolder").lastChild;
            if (tele !== null && tele.getAttribute("data-mgsc-shown") === "false") {
                var toast = bootstrap.Toast.getOrCreateInstance(tele);
                toast.show();
                tele.setAttribute("data-mgsc-shown", "true");
            }
        }
        """,
        Input("toastHolder", "children"),
        prevent_initial_call=True,
    )

    app.run(debug=False)
