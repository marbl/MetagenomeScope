#!/usr/bin/env python3

import os
import time
import logging
import dash
import dash_cytoscape as cyto
from dash import html, callback, Input, Output, State
from . import defaults
from .log_utils import start_log, log_lines_with_sep
from .config import SEPBIG, SEPSML
from .graph import AssemblyGraph


def run(
    graph: str = None,
    verbose: bool = defaults.VERBOSE,
):
    """Reads the graph and starts a Flask server for visualizing it.

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
        nodes.append({"data": {"id": str(n), "label": ag.nodeid2obj[n].name}})
    for e in ag.graph.edges:
        edges.append({"data": {"source": str(e[0]), "target": str(e[1])}})

    # update_title=None prevents Dash's default "Updating..." page title change
    app = dash.Dash(__name__, title="MgSc", update_title=None)
    CONTROLS_TOGGLER_ICON_CLASSES = "glyphicon glyphicon-menu-hamburger"
    app.layout = html.Div(
        [
            # controls toggler (hamburger button)
            html.Div(
                html.Span(
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
                        style={"font-family": "monospace"},
                    ),
                    html.P([f"{len(nodes):,} nodes, {len(edges):,} edges."]),
                    html.P([f"{ag.num_ccs:,} components."]),
                    html.P(
                        [
                            html.Button(
                                [
                                    html.Span(
                                        className="glyphicon glyphicon-pencil"
                                    ),
                                    # the old way of having a &nbsp; between the
                                    # icon and the label doesn't seem to be
                                    # supported in Dash. Can recreate with padding:
                                    # https://community.plotly.com/t/how-to-leave-some-space-on-the-page-between-graphs-and-drop-down-menus/6234/2
                                    html.Span(
                                        "Draw", style={"padding-left": "0.7em"}
                                    ),
                                ],
                                id="drawButton",
                                className="btn btn-default drawCtrl",
                            )
                        ]
                    ),
                ],
                id="controls",
                style={
                    "position": "absolute",
                    "top": "0em",
                    "bottom": "0em",
                    "left": "0em",
                    "width": "20em",
                    "text-align": "center",
                    # only show the scrollbar when needed - firefox doesn't
                    # seem to need this, but chrome does
                    "overflow-y": "auto",
                    "z-index": "1",
                    "background-color": "#123",
                    "color": "#ccc",
                    "border-right": "0.5em solid #002",
                },
                className="",
            ),
            # cy
            html.Div(
                id="cyDiv",
                style={
                    "position": "absolute",
                    "left": "20em",
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
                    "transition": "left 0.2s",
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
        if "notviewable" in controls_classes:
            # Make the control panel visible again
            cy_div_style["left"] = "20em"
            return ("", CONTROLS_TOGGLER_ICON_CLASSES, cy_div_style)
        else:
            # Hide the control panel
            cy_div_style["left"] = "0em"
            return (
                "notviewable",
                CONTROLS_TOGGLER_ICON_CLASSES + " darkToggler",
                cy_div_style,
            )

    @callback(
        Output("cyDiv", "children"),
        Input("drawButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def draw(n_clicks):
        return cyto.Cytoscape(
            id="cy",
            elements=nodes + edges,
            layout={"name": "circle"},
            style={
                "width": "100%",
                "height": "100%",
            },
        )

    app.run(debug=True)
