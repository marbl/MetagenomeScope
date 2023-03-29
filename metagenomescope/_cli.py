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
####
# Structure of this file adapted roughly from
# https://github.com/biocore/qurro/blob/master/qurro/scripts/_plot.py.

import click
from .config import MAXN_DEFAULT, MAXE_DEFAULT
from .main import make_viz
from ._param_descriptions import INPUT, OUTPUT_DIR, MAXN, MAXE, PATTERNS_FLAG


# Make mgsc -h (or just mgsc by itself) show the help text
@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.option("-i", "--input-file", required=True, help=INPUT)
@click.option("-o", "--output-dir", required=True, help=OUTPUT_DIR)
# @click.option(
#    "-ao",
#    "--assume-oriented",
#    required=False,
#    default=False,
#    help=ASSUME_ORIENTED,
# )
@click.option(
    "-maxn",
    "--max-node-count",
    required=False,
    default=MAXN_DEFAULT,
    help=MAXN,
    show_default=True,
)
@click.option(
    "-maxe",
    "--max-edge-count",
    required=False,
    default=MAXE_DEFAULT,
    help=MAXE,
    show_default=True,
)
@click.option(
    "--patterns/--no-patterns",
    is_flag=True,
    default=True,
    show_default=True,
    help=PATTERNS_FLAG,
)
# @click.option(
#    "-mbf", "--metacarvel-bubble-file", required=False, default=None, help=MBF
# )
# @click.option(
#    "-up", "--user-pattern-file", required=False, default=None, help=UP
# )
# @click.option(
#    "-spqr",
#    "--compute-spqr-data",
#    required=False,
#    is_flag=True,
#    default=False,
#    help=SPQR,
# )
# @click.option(
#    "-sp",
#    "--save-structural-patterns",
#    is_flag=True,
#    required=False,
#    default=False,
#    help=STRUCTPATT,
# )
# @click.option(
#    "-pg",
#    "--preserve-gv",
#    is_flag=True,
#    required=False,
#    default=False,
#    help=PG,
# )
# @click.option(
#    "-px",
#    "--preserve-xdot",
#    required=False,
#    is_flag=True,
#    default=False,
#    help=PX,
# )
# @click.option(
#    "-nbdf",
#    "--save-no-backfill-dot-files",
#    is_flag=True,
#    required=False,
#    default=False,
#    help=NBDF,
# )
# @click.option(
#    "-npdf",
#    "--save-no-pattern-dot-files",
#    is_flag=True,
#    required=False,
#    default=False,
#    help=NPDF,
# )
def run_script(
    input_file: str,
    output_dir: str,
    # assume_oriented: bool,
    max_node_count: int,
    max_edge_count: int,
    patterns: bool,
    # metacarvel_bubble_file: str,
    # user_pattern_file: str,
    # compute_spqr_data: bool,
    # save_structural_patterns: bool,
    # preserve_gv: bool,
    # preserve_xdot: bool,
    # save_no_backfill_dot_files: bool,
    # save_no_pattern_dot_files: bool,
) -> None:
    """Creates a visualization of an assembly graph.

    This creates a folder containing an interactive HTML/JS visualization of
    the graph. The folder's index.html file can be opened in a web browser to
    access the visualization.

    There are many options available to customize the visualization / output,
    but the two most important ones are the input file and output directory:
    generating a visualization can be as simple as

        mgsc -i graph.gfa -o viz

    ...which will generate an output directory named "viz". (You'll need to
    replace "graph.gfa" with whatever the path to your assembly graph is.)
    """
    if not patterns:
        raise NotImplementedError("uhhh")
    make_viz(
        input_file,
        output_dir,
        # assume_oriented,
        max_node_count,
        max_edge_count,
        # metacarvel_bubble_file,
        # user_pattern_file,
        # compute_spqr_data,
        # save_structural_patterns,
        # preserve_gv,
        # preserve_xdot,
        # save_no_backfill_dot_files,
        # save_no_pattern_dot_files,
    )


if __name__ == "__main__":
    run_script()
