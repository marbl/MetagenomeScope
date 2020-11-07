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
import jinja2
from . import graph_objects, arg_utils
from .msg_utils import operation_msg, conclude_msg


def make_viz(
    input_file: str,
    output_dir: str,
    assume_oriented: bool,
    max_node_count: int,
    max_edge_count: int,
    metacarvel_bubble_file: str,
    user_pattern_file: str,
    spqr: bool,
    sp: bool,
    pg: bool,
    px: bool,
    nbdf: bool,
    npdf: bool,
):
    """Creates a visualization.

    NOTE: Not all arguments are supported yet.
    TODOs:
        -assume oriented

        -metacarvel bubble file
        -user pattern file

        -spqr

        -sp
        -pg
        -px
        -nbdf
        -npdf
    """
    arg_utils.check_dir_existence(output_dir)
    arg_utils.validate_max_counts(max_node_count, max_edge_count)

    bn = os.path.basename(input_file)
    operation_msg("Reading and parsing input file {}...".format(bn))
    asm_graph = graph_objects.AssemblyGraph(
        input_file,
        max_node_count=max_node_count,
        max_edge_count=max_edge_count,
    )
    conclude_msg()

    # Identify patterns, do layout, etc.
    asm_graph.process()

    return

    operation_msg(
        "Writing graph data to the output directory, {}...".format(output_dir)
    )
    # Make the output directory.
    arg_utils.create_output_dir(output_dir)

    # TODO: Copy "support files" to output directory (see Qurro)
    pass

    # Get JSON representation of the graph data.
    graph_data = asm_graph.to_dict()

    # TODO: Load the index.html file in the output directory
    pass

    # TODO: Using Jinja2, populate the {{ dataJSON }} tag in the HTML file with
    # the output of asm_graph.to_dict()
    pass

    conclude_msg()

    # Other TODO items:
    # -Identify user-supplied bubbles and patterns. Should be "lowest level"
    #  patterns, i.e. collapsed first.
    # -Use fancier complex bubble detection, similar to
    #  what's described in the MaryGold / MetaFlye papers. For now very complex
    #  bubbles are assumed to be covered by decomposition or by user input, but
    #  this will not always be the case.
    # -If -spqr passed, compute SPQR trees and record composition/structure.
    # -Output identified pattern info if -sp passed
    # -SPQR layout!
