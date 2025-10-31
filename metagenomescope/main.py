#!/usr/bin/env python3

import logging
import dash
import dash_cytoscape as cyto
from dash import html, callback, Input, Output, State
from . import defaults, cy_config
from .log_utils import start_log, log_lines_with_sep
from .misc_utils import pluralize
from .css_config import (
    CONTROLS_WIDTH,
    CONTROLS_BORDER_THICKNESS,
    CONTROLS_TRANSITION_DURATION,
)
from .graph import AssemblyGraph


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

    nodes = []
    edges = []
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
                "data": {"id": str(n), "label": nobj.name},
                "classes": ndir,
            }
        )
    for e in ag.graph.edges:
        edges.append({"data": {"source": str(e[0]), "target": str(e[1])}})

    ctrl_sep = html.Div(
        style={
            "width": "100%",
            "height": CONTROLS_BORDER_THICKNESS,
            "background-color": "#002",
            "margin": "1.25em 0",
        }
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
                        [ag.basename],
                        style={
                            "font-family": "monospace",
                            "margin-top": "2em",
                        },
                    ),
                    html.P(
                        [
                            f"{pluralize(len(nodes), 'node')}, "
                            f"{pluralize(len(edges), 'edge')}."
                        ]
                    ),
                    html.P([f"{pluralize(len(ag.components), 'component')}."]),
                    ctrl_sep,
                    html.H4("Draw"),
                    html.P(
                        [
                            html.Button(
                                [
                                    html.I(className="bi bi-brush"),
                                    # the old way of having a &nbsp; between the
                                    # icon and the label doesn't seem to be
                                    # supported in Dash. Can recreate with padding:
                                    # https://community.plotly.com/t/how-to-leave-some-space-on-the-page-between-graphs-and-drop-down-menus/6234/2
                                    html.Span(
                                        "Draw", style={"padding-left": "0.7em"}
                                    ),
                                ],
                                id="drawButton",
                                className="btn btn-light drawCtrl",
                                type="button",
                            )
                        ]
                    ),
                    ctrl_sep,
                    html.H4("Selected"),
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
