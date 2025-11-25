#!/usr/bin/env python3

import click
from . import __version__, defaults, descs, config, main


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
    help=descs.GRAPH,
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
@click.option(
    "-p",
    "--port",
    type=click.IntRange(min=config.MIN_PORT),
    default=defaults.PORT,
    show_default=True,
    help=descs.PORT,
)
@click.option(
    "--verbose/--no-verbose",
    is_flag=True,
    default=defaults.VERBOSE,
    show_default=True,
    help=descs.VERBOSE,
)
@click.version_option(__version__, "-v", "--version")
def run_script(
    graph: str,
    port: int,
    verbose: bool,
) -> None:
    """Visualizes an assembly graph.

    Please check out https://github.com/marbl/MetagenomeScope if you have any
    questions, suggestions, etc. about this tool.
    """
    main.run(
        graph=graph,
        port=port,
        verbose=verbose,
    )


if __name__ == "__main__":
    run_script()
