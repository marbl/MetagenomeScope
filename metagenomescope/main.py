#!/usr/bin/env python3

import logging
import math
import base64
import dash
import dash_cytoscape as cyto
import plotly.graph_objects as go
import plotly.express as px
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
from io import BytesIO
from . import defaults, cy_config, css_config, ui_utils
from .log_utils import start_log, log_lines_with_sep
from .misc_utils import pluralize
from .graph import AssemblyGraph, graph_utils
from .errors import WeirdError, UIError


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
            html.I(className="bi bi-sort-down"),
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
                        style={"margin-top": "0.7em"},
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
                                # the first arg lists the options,
                                # the second arg lists the ones that are
                                # by default selected
                                ["Show patterns"],
                                ["Show patterns"],
                            ),
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
                                                                            str(
                                                                                len(
                                                                                    ag.components
                                                                                )
                                                                            ),
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
                                                                        "Histogram of nodes/edges",
                                                                        className="nav-link active",
                                                                        id="ccNestHistTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestHistTabPane",
                                                                            "aria-controls": "ccNestHistTabPane",
                                                                            "aria-selected": "true",
                                                                        },
                                                                    ),
                                                                    className="nav-item",
                                                                    role="presentation",
                                                                ),
                                                                html.Li(
                                                                    html.Button(
                                                                        "Scatterplot of nodes/edges",
                                                                        className="nav-link",
                                                                        id="ccNestScatterTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestScatterTabPane",
                                                                            "aria-controls": "ccNestScatterTabPane",
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
                                                                        id="ccHistContainer",
                                                                    ),
                                                                    className="tab-pane fade show active",
                                                                    id="ccNestHistTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestHistTab"
                                                                    },
                                                                ),
                                                                html.Div(
                                                                    html.Div(
                                                                        id="ccScatterContainer",
                                                                    ),
                                                                    className="tab-pane fade",
                                                                    id="ccNestScatterTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestScatterTab"
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
        ],
    )

    if multiple_ccs:

        @callback(
            Output("ccHistContainer", "children"),
            Input("ccTab", "n_clicks"),
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
            Output("ccScatterContainer", "children"),
            Input("ccNestScatterTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_scatter(n_clicks):
            graph_utils.validate_multiple_ccs(ag)
            cc_node_cts, cc_edge_cts = ag.get_component_node_and_edge_cts()

            # Plotly's WebGL rendering should hold up well for big datasets:
            # https://plotly.com/python/performance/
            fig = px.scatter(
                x=cc_node_cts,
                y=cc_edge_cts,
                marginal_x="histogram",
                marginal_y="histogram",
                render_mode="webgl",
            )
            # The scatterplot is the 0-th plot, and the two marginal histograms
            # are the remaining plots in indices 1 and 2. We don't want to
            # apply all the styling of the scatterplot to the histograms (which
            # is what happens if we call fig.update_traces()), so we can index
            # fig.data to selectively do styling stuff per
            # https://community.plotly.com/t/getting-trace-from-figure/68708/6
            #
            # I am SURE there is a less jank way to do this but idk what
            for i in (0, 1, 2):
                fig.data[i].marker.color = "#16a"
                fig.data[i].marker.line.width = 2
                fig.data[i].marker.line.color = "#003"
            # (If we try to set the marker size of the histograms then Plotly
            # raises an error)
            fig.data[0].marker.size = 20
            # (Setting the opacity on the histograms actually works, it just
            # looks too faint compared to the default opacity imo)
            fig.data[0].marker.opacity = 0.4
            # Make hovering over points in the scatterplot say "# nodes"
            # instead of "x". We could also update hover templates for the
            # marginal histograms but there is some jank about WHICH of {1,2}
            # corresponds to which histogram and I don't want to worry about
            # testing that now so I'm gonna leave it as is
            fig.data[0].hovertemplate="# nodes: %{x}<br># edges: %{y}"
            fig.update_layout(
                title_text="Numbers of nodes and edges per component",
                xaxis_title_text="# nodes",
                yaxis_title_text="# edges",
                font=dict(size=16),
                title=dict(yanchor="bottom", y=1, yref="paper"),
                title_pad=dict(b=30),
                margin=dict(t=75),
            )
            fig.update_yaxes(ticksuffix=" ")
            # On interactive scatterplots, I think it is natural to expect that
            # zooming the mouse wheel will also zoom in/out of the graph. This
            # can be enabled using this config setting. From
            # https://community.plotly.com/t/zoom-on-mouse-wheel/477/9
            return dcc.Graph(figure=fig, config={"scrollZoom": True})

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
        Output("toastHolder", "children"),
        Output("cyDiv", "children"),
        State("toastHolder", "children"),
        State("cyDiv", "children"),
        State("ccDrawingSelect", "value"),
        State("ccSizeRankSelector", "value"),
        State("ccNodeNameSelector", "value"),
        Input("drawButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def draw(
        curr_toasts,
        curr_cy,
        cc_drawing_selection_type,
        size_rank,
        node_name,
        n_clicks,
    ):
        logging.debug("Received request to draw the graph.")
        ag_selection_params = {}

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
                    curr_cy,
                )
            ag_selection_params = {"cc_size_rank": size_rank}

        elif cc_drawing_selection_type == "ccDrawingNodeName":
            # looks like not typing in the node name field at all results
            # in node_name being None. However, if we type something in and
            # then fully delete it, then node_name becomes "". Eesh!
            if node_name is None or node_name == "":
                return (
                    ui_utils.add_error_toast(
                        curr_toasts, "Draw Error", "No node name specified."
                    ),
                    curr_cy,
                )
            ag_selection_params = {"cc_node_name": node_name}

        # if something goes wrong during drawing, propagate the result to
        # a toast message in the browser without changing the cytoscape div
        try:
            logging.debug(
                "Converting graph to Cytoscape.js-compatible elements ("
                f"parameters {ag_selection_params})..."
            )
            elements = ag.to_cyjs_elements(**ag_selection_params)
            logging.debug("...Done.")
        except UIError as err:
            logging.debug(
                "...Something went wrong; propagating error message to user."
            )
            return (
                ui_utils.add_error_toast(curr_toasts, "Draw Error", str(err)),
                curr_cy,
            )

        # TODO store info in AsmGraph? about which ccs have been laid out.
        # For now, we can assume that the scaling stuff is not configurable,
        # so there is only a binary of "laid out" or "not laid out". Set up
        # UI elements in the viz to - like before - let user select one cc,
        # all ccs, or cc containing a given node to lay out. These will update
        # the layout status for either 1 or all ccs. Then, here, when we go
        # to draw some portion of the graph, we can figure out what parts of
        # layout we may have to redo if necessary. Eventually we can add
        # progress bars here or something to the viz but for now nbd
        # if not ag.layout_done:
        #     ag.layout()
        return curr_toasts, cyto.Cytoscape(
            id="cy",
            elements=elements,
            layout={"name": "cose"},
            style={
                "width": "100%",
                "height": "100%",
            },
            boxSelectionEnabled=True,
            maxZoom=9,
            stylesheet=[
                {
                    "selector": "node",
                    "style": {
                        "background-color": cy_config.NODE_COLOR,
                        "color": cy_config.UNSELECTED_NODE_FONT_COLOR,
                        "label": "data(label)",
                        "text-valign": "center",
                        "min-zoomed-font-size": "12",
                        "z-index": "2",
                    },
                },
                {
                    "selector": "node:selected",
                    "style": {
                        "color": cy_config.SELECTED_NODE_FONT_COLOR,
                        "background-blacken": cy_config.SELECTED_NODE_BLACKEN,
                    },
                },
                {
                    "selector": "node.fwd",
                    "style": {
                        "shape": "polygon",
                        "shape-polygon-points": cy_config.FWD_NODE_POLYGON_PTS,
                    },
                },
                {
                    "selector": "node.rev",
                    "style": {
                        "shape": "polygon",
                        "shape-polygon-points": cy_config.REV_NODE_POLYGON_PTS,
                    },
                },
                {
                    "selector": "node.unoriented",
                    "style": {
                        "shape": cy_config.UNORIENTED_NODE_SHAPE,
                    },
                },
            ],
        )

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

    app.run(debug=True)
