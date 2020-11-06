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
        max_edge_count=max_edge_count
    )
    conclude_msg()

    operation_msg("Scaling nodes based on lengths...")
    asm_graph.scale_nodes()
    asm_graph.compute_node_dimensions()
    conclude_msg()

    # TODO: don't display this if no edge weight data available. right now it's
    # ok tho since scale_edges() detects that case and behaves accordingly
    operation_msg("Attempting to scale edges based on weights...")
    asm_graph.scale_edges()
    conclude_msg()

    # Create the output directory now (since we know the graph is probably ok).
    # We do this up here so that we can output pattern files, etc.
    arg_utils.create_output_dir(output_dir)

    # Hierarchically decompose graph, creating duplicate nodes where needed
    # TODO: Have this utilize user-supplied bubbles and patterns. They should
    # be "lowest level" patterns, i.e. collapsed first.
    # ALSO TODO: Have this use fancier complex bubble detection, similar to
    # what's described in the MaryGold / MetaFlye papers. For now very complex
    # bubbles are assumed to be covered by decomposition or by user input, but
    # this will not always be the case.
    operation_msg("Running hierarchical pattern decomposition...")
    asm_graph.hierarchically_identify_patterns()
    conclude_msg()

    operation_msg("Laying out the graph...", True)
    asm_graph.layout()
    operation_msg("...Finished laying out the graph.", True)

    # Immediate TODO:
    # -Compute graph layouts. For each component:
    #   -Lay out individual patterns, starting at lowest level and moving up.
    #    Similar to SPQR layout code.
    #   -Finally, lay out the entire graph for the component, with patterns
    #    replaced with their bounding box.
    #   -Backfill all node/edge coordinates in.
    #
    #   At this point we can create AssemblyGraph.to_dot(), to_cytoscape(),
    #   etc. methods for temporary testing.
    #
    # -Use jinja2 to pass data to the viewer index.html file.
    #
    # -Modify the JS to prepare the graph summary, etc. and get ready for
    #  component drawing. Replace DB operations with just looking at the JSON.

    # TODO from here on down.
    # -Identify user-supplied bubbles.
    # -Identify user-supplied misc. patterns.
    # -If -spqr passed, compute SPQR trees and record composition/structure.
    # -Output identified pattern info if -sp passed
    # -Identify connected components for the "single" graph (SPQR mode).
    # -Identify connected components for the "normal" graph (non-SPQR mode).
    # -Compute node scaling for each connected component
    # -Compute edge scaling for each connected component
    # -SPQR layout!
    # -Normal layout!
