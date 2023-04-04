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
from distutils.dir_util import copy_tree
import jinja2
from . import graph, arg_utils
from .msg_utils import operation_msg, conclude_msg


def make_viz(
    input_file: str,
    output_dir: str,
    # assume_oriented: bool,
    max_node_count: int,
    max_edge_count: int,
    patterns: bool,
    # metacarvel_bubble_file: str,
    # user_pattern_file: str,
    # spqr: bool,
    # sp: bool,
    # pg: bool,
    # px: bool,
    # nbdf: bool,
    # npdf: bool,
):
    """Creates a visualization.

    Using MetagenomeScope's command-line interface will cause this function to
    be called, but -- if you'd like to -- you can just call this yourself from
    Python (e.g. if you want to procedurally create lots of visualizations).

    Parameters
    ----------
    input_file: str
        Path to the assembly graph to be visualized.

    output_dir: str
        Output directory to which the visualization will be written.

    max_node_count: int
        We won't visualize connected components containing more nodes than
        this.

    max_edge_count: int
        Like max_node_count, but for edges.

    patterns: bool
        If True, identify and highlight structural patterns; if False, don't.

    Returns
    -------
    None
    """
    arg_utils.check_dir_existence(output_dir)
    arg_utils.validate_max_counts(max_node_count, max_edge_count)

    # Read the assembly graph file and create an object representing it.
    operation_msg("Loading the assembly graph...")
    asm_graph = graph.AssemblyGraph(
        input_file,
        max_node_count=max_node_count,
        max_edge_count=max_edge_count,
        patterns=patterns,
    )
    conclude_msg()

    # Identify patterns (if patterns is True), do layout, etc.
    asm_graph.process()

    # Get JSON representation of the graph data.
    graph_data = asm_graph.to_json()

    operation_msg(
        "Writing graph data to the output directory, {}...".format(output_dir)
    )

    # Make the output directory.
    arg_utils.create_output_dir(output_dir)

    # Copy "support files" to output directory. (This part of code taken from
    # https://github.com/biocore/qurro/blob/master/qurro/generate.py, in the
    # gen_visualization() function.)
    #
    # First, figure out where this file (main.py) is, since support_files/ is
    # located alongside it.
    curr_loc = os.path.dirname(os.path.realpath(__file__))
    support_files_loc = os.path.join(curr_loc, "support_files")
    copy_tree(support_files_loc, output_dir)

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
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(output_dir))

    mainjs_template = env.get_template("main.js")
    with open(os.path.join(output_dir, "main.js"), "w") as mainjs_file:
        mainjs_file.write(mainjs_template.render({"dataJSON": graph_data}))

    index_template = env.get_template("index.html")
    with open(os.path.join(output_dir, "index.html"), "w") as index_file:
        index_file.write(
            index_template.render({"graphFilename": asm_graph.basename})
        )

    conclude_msg()
