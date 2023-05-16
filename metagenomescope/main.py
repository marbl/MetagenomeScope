#!/usr/bin/env python3.6
# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
from distutils.dir_util import copy_tree
import jinja2
from . import graph, __version__
from .msg_utils import operation_msg, conclude_msg
from .file_utils import create_output_dir
from .config import SEPARATOR_CHAR


def make_viz(
    input_file: str,
    max_node_count: int,
    max_edge_count: int,
    patterns: bool,
    output_viz_dir: str,
    output_dot: str,
    output_ccstats: str,
):
    """Creates a visualization.

    Using MetagenomeScope's command-line interface will cause this function to
    be called, but -- if you'd like to -- you can just call this yourself from
    Python (e.g. if you want to procedurally create lots of visualizations).

    Parameters
    ----------
    input_file: str
        Path to the assembly graph to be visualized.

    max_node_count: int
        We won't visualize connected components containing more nodes than
        this.

    max_edge_count: int
        Like max_node_count, but for edges.

    patterns: bool
        If True, identify and highlight structural patterns; if False, don't.

    output_viz_dir: str or None
        If passed, we'll write the visualization to this output directory.

    output_dot: str or None
        If passed, we'll write out a DOT file to this filepath.

    output_ccstats: str or None
        If passed, we'll write out cc stats to this filepath.

    Returns
    -------
    None
    """
    t0 = time.time()
    # Log the version, just for reference -- based on this blog post:
    # http://lh3.github.io/2022/09/28/additional-recommendations-for-creating-command-line-interfaces
    first_line = f"Running MetagenomeScope (version {__version__})..."
    second_line = SEPARATOR_CHAR * len(first_line)
    operation_msg(f"{first_line}\n{second_line}", newline=True)

    # Read the assembly graph file and create an object representing it.
    # Creating the AssemblyGraph object will identify patterns, scale nodes and
    # edges, etc.
    asm_graph = graph.AssemblyGraph(
        input_file,
        max_node_count=max_node_count,
        max_edge_count=max_edge_count,
        patterns=patterns,
    )

    outputs = []

    if output_dot is not None:
        asm_graph.to_dot(output_dot)
        outputs.append("a DOT file")

    if output_ccstats is not None:
        asm_graph.to_tsv(output_ccstats)
        outputs.append("a TSV file")

    if output_viz_dir is not None:
        # We need to lay out the graph. This can be a time-consuming process,
        # which is why it isn't automatically done when we create an
        # AssemblyGraph object.
        asm_graph.layout()

        # Get JSON representation of the graph data.
        graph_data = asm_graph.to_json()

        operation_msg(
            "Writing the visualization to the output directory, "
            f'"{output_viz_dir}"...'
        )

        create_output_dir(output_viz_dir)

        # Copy "support files" to output directory. (This part of code taken from
        # https://github.com/biocore/qurro/blob/master/qurro/generate.py, in the
        # gen_visualization() function.)
        #
        # First, figure out where this file (main.py) is, since support_files/ is
        # located alongside it.
        curr_loc = os.path.dirname(os.path.realpath(__file__))
        support_files_loc = os.path.join(curr_loc, "support_files")
        copy_tree(support_files_loc, output_viz_dir)

        # Using Jinja2, populate the {{ dataJSON }} tag in the main.js file with
        # the JSON representation of the graph data.
        #
        # Also, populate the {{ graphFilename }} tag in the index.html file, so we
        # can show the filename in the application title (this way the title is
        # shown immediately, rather than flickering when the page is loaded).
        # (... This is obviously much less important than the first thing, but it's
        # a nice little detail that should help users if they have many MgSc tabs
        # open at once.)
        #
        # This part of code taken from
        # https://github.com/biocore/empress/blob/master/empress/core.py, in
        # particular _get_template() and make_empress(), and
        # https://github.com/biocore/empress/blob/master/tests/python/make-dev-page.py.
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(output_viz_dir)
        )

        mainjs_template = env.get_template("main.js")
        with open(os.path.join(output_viz_dir, "main.js"), "w") as mainjs_file:
            mainjs_file.write(mainjs_template.render({"dataJSON": graph_data}))

        index_template = env.get_template("index.html")
        with open(
            os.path.join(output_viz_dir, "index.html"), "w"
        ) as index_file:
            index_file.write(
                index_template.render({"graphFilename": asm_graph.basename})
            )

        outputs.append("an interactive visualization")
        conclude_msg()

    t1 = time.time()
    duration = t1 - t0
    llprefix = "MetagenomeScope "
    if len(outputs) == 0:
        llprefix += "didn't create anything (no output options were specified)"
    else:
        if len(outputs) == 1:
            output_str = outputs[0]
        elif len(outputs) == 2:
            output_str = f"{outputs[0]} and {outputs[1]}"
        else:
            output_str = ", ".join(outputs[:-1]) + f", and {outputs[-1]}"
        llprefix += f"successfully created {output_str}"
    last_line = f"{llprefix}, and ran for {duration:,.2f} seconds."
    penultimate_line = SEPARATOR_CHAR * len(last_line)
    operation_msg(f"{penultimate_line}\n{last_line}", newline=True)
