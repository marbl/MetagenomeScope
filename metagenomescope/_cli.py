#!/usr/bin/env python3

import click
from . import __version__, defaults, descs, config, main


@click.command(
    context_settings={
        # Make mgsc -h (or just mgsc by itself) show the help text
        "help_option_names": ["-h", "--help"],
        # I'm extremely petty and I want the CLI options to take up at most
        # one line each if possible, and this is necessary to get the --port
        # and --graph options to take up just one line. Click's default of
        # 80 is probably way too short for most modern displays anyway.
        "max_content_width": 87,
    },
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
@click.option(
    "-a",
    "--agp",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=False,
    help=descs.AGP,
)
@click.option(
    "-p",
    "--port",
    type=click.IntRange(min=config.MIN_PORT, max=config.MAX_PORT),
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
@click.option(
    "--debug/--no-debug",
    is_flag=True,
    default=defaults.DEBUG,
    show_default=True,
    help=descs.DEBUG,
)
@click.version_option(__version__, "-v", "--version")
def run_script(
    graph: str,
    agp: str,
    port: int,
    verbose: bool,
    debug: bool,
) -> None:
    """Visualizes an assembly graph.

    Please visit https://github.com/marbl/MetagenomeScope for more information.
    """
    main.run(
        graph=graph,
        agp=agp,
        port=port,
        verbose=verbose,
        debug=debug,
    )


if __name__ == "__main__":
    run_script()
