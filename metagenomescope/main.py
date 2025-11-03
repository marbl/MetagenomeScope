#!/usr/bin/env python3

import logging
import base64
import matplotlib
import dash
import dash_cytoscape as cyto
import plotly.express as px
from dash import html, callback, dcc, Input, Output, State
from io import BytesIO
from matplotlib import pyplot
from . import defaults, cy_config
from .log_utils import start_log, log_lines_with_sep
from .misc_utils import pluralize
from .css_config import (
    CONTROLS_WIDTH,
    CONTROLS_BORDER_THICKNESS,
    CONTROLS_TRANSITION_DURATION,
)
from .graph import AssemblyGraph

# account for tkinter crashing: https://stackoverflow.com/a/51178529
matplotlib.use("Agg")


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

    # TODO have AssemblyGraph produce dict with elements incl decomposed nodes and edges

    nodes = []
    edges = []
    # TODO this is just getting the first (biggest) cc. make user selectable ofc
    for n in ag.graph.nodes:
        nobj = ag.nodeid2obj[n]
        if "orientation" in nobj.data:
            if nobj.data["orientation"] == "+":
                ndir = "fwd"
            else:
                ndir = "rev"
        else:
            ndir = "unoriented"
        nodes.append(
            {
                "data": {"id": str(nobj.unique_id), "label": nobj.name},
                "classes": ndir,
            }
        )
    for e in ag.graph.edges:
        edges.append(
            {
                "data": {
                    "source": str(e[0]),
                    "target": str(e[1]),
                }
            }
        )

    ctrl_sep = html.Div(
        style={
            "width": "100%",
            "height": CONTROLS_BORDER_THICKNESS,
            "background-color": "#002",
            "margin": "1.25em 0",
        },
        className="ctrlSep",
    )

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
                            f"{pluralize(len(nodes), 'node')}, "
                            f"{pluralize(len(edges), 'edge')}."
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
                    html.P(
                        [
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
                            )
                        ]
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
                    "width": CONTROLS_WIDTH,
                    "text-align": "center",
                    # only show the scrollbar when needed - firefox doesn't
                    # seem to need this, but chrome does
                    "overflow-y": "auto",
                    "z-index": "1",
                    "background-color": "#123",
                    "color": "#ccc",
                    "border-right": f"{CONTROLS_BORDER_THICKNESS} solid #002",
                    "transition": f"left {CONTROLS_TRANSITION_DURATION}",
                },
                className="",
            ),
            # cy
            html.Div(
                id="cyDiv",
                style={
                    "position": "absolute",
                    "left": CONTROLS_WIDTH,
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
                    "transition": f"left {CONTROLS_TRANSITION_DURATION}",
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
                                            html.Li(
                                                html.Button(
                                                    "Histograms",
                                                    className="nav-link",
                                                    id="histTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#histTabPane",
                                                        "aria-controls": "histTabPane",
                                                        "aria-selected": "false",
                                                    },
                                                ),
                                                className="nav-item",
                                                role="presentation",
                                            ),
                                            html.Li(
                                                html.Button(
                                                    "Treemaps",
                                                    className="nav-link",
                                                    id="treemapTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#treemapTabPane",
                                                        "aria-controls": "treemapTabPane",
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
                                                                            f"{len(nodes):,}",
                                                                        ),
                                                                        html.Td(
                                                                            f"{len(edges):,}",
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
                                                        className="table table-striped-columns",
                                                    ),
                                                    html.P(
                                                        "Note that, as of writing, these counts include "
                                                        "both + and - copies of nodes / edges / components."
                                                    ),
                                                    html.P(
                                                        "This is subject to change in the future."
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
                                            html.Div(
                                                [
                                                    html.H5(
                                                        "Components in the graph, by node count"
                                                    ),
                                                    html.P(
                                                        "(This is rendered as an image using matplotlib.)"
                                                    ),
                                                    html.Img(
                                                        id="histContainer",
                                                        # needed to center horizontally
                                                        # https://stackoverflow.com/a/45439817
                                                        style={
                                                            "margin": "0 auto",
                                                            "display": "block",
                                                        },
                                                    ),
                                                ],
                                                id="histTabPane",
                                                className="tab-pane fade show",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "histTab"
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.H5(
                                                        "Components in the graph, by node count"
                                                    ),
                                                    html.P(
                                                        "(This is rendered dynamically using Plotly.)"
                                                    ),
                                                    html.Div(
                                                        id="treemapContainer",
                                                    ),
                                                ],
                                                id="treemapTabPane",
                                                className="tab-pane fade",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "treemapTab"
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
        ],
    )

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
            # Make the control panel visible again
            cy_div_style["left"] = CONTROLS_WIDTH
            return ("", CONTROLS_TOGGLER_ICON_CLASSES, cy_div_style)
        else:
            # Hide the control panel
            cy_div_style["left"] = "0em"
            return (
                "offscreen-controls",
                CONTROLS_TOGGLER_ICON_CLASSES + " darkToggler",
                cy_div_style,
            )

    @callback(
        Output("histContainer", "src"),
        Input("infoButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def plot_hist(n_clicks):
        cc_sizes = [0]
        for cc in ag.components:
            cc_sizes.append(cc.num_total_nodes)
        # encode a static matplotlib image: https://stackoverflow.com/a/56932297
        # and https://matplotlib.org/stable/gallery/user_interfaces/web_application_server_sgskip.html
        with pyplot.style.context("ggplot"):
            fig, ax = pyplot.subplots(2, 1)
            ax[0].hist(
                cc_sizes,
                bins=range(0, 500, 10),
                color="#0a0",
                edgecolor="#030",
                lw=1,
            )
            ax[1].hist(
                cc_sizes,
                bins=range(0, 51, 1),
                color="#0a0",
                edgecolor="#030",
                lw=1,
            )
            ax[0].set_title("All components (bin size = 10)")
            ax[1].set_title("Just components with < 50 nodes")
            buf = BytesIO()
            ax[0].set_ylabel("# components")
            ax[1].set_ylabel("# components")
            ax[1].set_xlabel("# nodes in a component")
            fig.set_size_inches(10, 8)
            fig.savefig(buf, format="png", bbox_inches="tight")
            data = base64.b64encode(buf.getbuffer()).decode("ascii")
            buf.close()
        pyplot.close()
        return f"data:image/png;base64,{data}"

    @callback(
        Output("treemapContainer", "children"),
        Input("treemapTab", "n_clicks"),
        prevent_initial_call=True,
    )
    def plot_treemap(n_clicks):
        cc_names = ["Root"]
        cc_sizes = [0]
        cc_parents = [""] + (["Root"] * (len(ag.components)))
        for cci, cc in enumerate(ag.components, 1):
            cc_names.append(str(cci))
            cc_sizes.append(cc.num_total_nodes)
        fig = px.treemap(
            names=cc_names,
            values=cc_sizes,
            parents=cc_parents,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return dcc.Graph(figure=fig)

    # TODO remove when we do layout using Graphviz manually
    cyto.load_extra_layouts()

    @callback(
        Output("cyDiv", "children"),
        Input("drawButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def draw(n_clicks):
        return cyto.Cytoscape(
            id="cy",
            elements=nodes + edges,
            layout={"name": "dagre"},
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

    app.run(debug=True)
