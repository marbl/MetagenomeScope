#!/usr/bin/env python3

import os
import time
import logging
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
    asm_graph = AssemblyGraph(graph)
