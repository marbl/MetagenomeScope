#!/usr/bin/env python3

import click
from . import __version__
from ._param_descriptions import (
    GRAPH,
)
from .main import run


# Make mgsc -h (or just mgsc by itself) show the help text
@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.option(
    "-g",
    "--graph",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help=GRAPH,
)
# @click.option(
#     "-f",
#     "--fasta",
#     type=click.Path(exists=True, dir_okay=False, readable=True),
#     required=False,
#     help=FASTA,
# )
# @click.option(
#     "-a",
#     "--agp",
#     type=click.Path(exists=True, dir_okay=False, readable=True),
#     required=False,
#     help=AGP,
# )
# @click.option(
#     "-n",
#     "--node-metadata",
#     type=click.Path(exists=True, dir_okay=False, readable=True),
#     required=False,
#     default=None,
#     show_default=True,
#     help=NODE_METADATA,
# )
# @click.option(
#     "-e",
#     "--edge-metadata",
#     type=click.Path(exists=True, dir_okay=False, readable=True),
#     required=False,
#     default=None,
#     show_default=True,
#     help=EDGE_METADATA,
# )
@click.version_option(__version__, "-v", "--version")
def run_script(
    graph: str,
) -> None:
    """Visualizes an assembly graph.

    Please check out https://github.com/marbl/MetagenomeScope if you have any
    questions, suggestions, etc. about this tool.
    """
    run(
        graph,
    )


if __name__ == "__main__":
    run_script()
