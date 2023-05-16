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
from . import __version__
from .config import MAXN_DEFAULT, MAXE_DEFAULT
from .main import make_viz
from ._param_descriptions import (
    INPUT,
    OUTPUT_DIR,
    OUTPUT_CCSTATS,
    OUTPUT_DOT,
    MAXN,
    MAXE,
    PATTERNS_FLAG,
)


# Make mgsc -h (or just mgsc by itself) show the help text
@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.option(
    "-i",
    "--input-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help=INPUT,
)
@click.option(
    "-o",
    "--output-viz-dir",
    type=click.Path(exists=False),
    default=None,
    show_default=True,
    help=OUTPUT_DIR,
)
@click.option(
    "-od",
    "--output-dot",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    show_default=True,
    help=OUTPUT_DOT,
)
@click.option(
    "-os",
    "--output-ccstats",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    show_default=True,
    help=OUTPUT_CCSTATS,
)
@click.option(
    "-maxn",
    "--max-node-count",
    type=click.IntRange(min=0),
    required=False,
    default=MAXN_DEFAULT,
    show_default=True,
    help=MAXN,
)
@click.option(
    "-maxe",
    "--max-edge-count",
    type=click.IntRange(min=0),
    required=False,
    default=MAXE_DEFAULT,
    show_default=True,
    help=MAXE,
)
@click.option(
    "--patterns/--no-patterns",
    is_flag=True,
    default=True,
    show_default=True,
    help=PATTERNS_FLAG,
)
@click.version_option(__version__, "-v", "--version")
def run_script(
    input_file: str,
    output_viz_dir: str,
    output_dot: str,
    output_ccstats: str,
    max_node_count: int,
    max_edge_count: int,
    patterns: bool,
) -> None:
    """Visualizes and/or summarizes an assembly graph.

    MetagenomeScope supports multiple types of output (-o, -od, -os);
    you will probably want to start with -o.

    Please check out https://github.com/marbl/MetagenomeScope if you have any
    questions, suggestions, etc. about this tool.
    """
    make_viz(
        input_file,
        max_node_count,
        max_edge_count,
        patterns,
        output_viz_dir,
        output_dot,
        output_ccstats,
    )


if __name__ == "__main__":
    run_script()
