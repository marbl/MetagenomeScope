#!/usr/bin/env python3

import os
import time
import logging
import dash
import dash_cytoscape as cyto
from dash import html
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

    # for dagre. remove when we get graphviz layouts back in
    cyto.load_extra_layouts()
    app = dash.Dash(__name__, title="MgSc")
    app.layout = html.Div(
        [
            # controls
            html.Div(
                [
                    html.H4(
                        [ag.basename],
                        style={"font-family": "monospace"},
                    ),
                    html.P([f"{len(nodes):,} nodes, {len(edges):,} edges."]),
                ],
                style={
                    "position": "absolute",
                    "width": "20em",
                    "top": "0em",
                    "bottom": "0em",
                    "text-align": "center",
                    "overflow-y": "auto",
                    "z-index": "1",
                    "background-color": "#123",
                    "color": "#ccc",
                    "border-right": "0.5em solid #002",
                },
            ),
            # cy
            cyto.Cytoscape(
                id="cy",
                elements=nodes + edges,
                layout={"name": "dagre"},
                style={
                    "position": "absolute",
                    "left": "20em",
                    "right": "0em",
                    "top": "0em",
                    "bottom": "0em",
                    "border": "1px solid black",
                },
            ),
        ],
    )
    app.run(debug=True)
