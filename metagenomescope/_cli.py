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
# Manages the main command-line interface (CLI) of MetagenomeScope.

import sys
import os
import argparse

from . import config
from .collate import collate_graph

# Define supported command-line arguments. (We don't actually run
# parser.parse_args() until later on, in order to support use of this file
# aside from as a script.)
parser = argparse.ArgumentParser(description=config.COLLATE_DESCRIPTION)
parser.add_argument(
    "-i",
    "--inputfile",
    required=True,
    help="""input assembly
    graph filename (LastGraph, GFA, or MetaCarvel GML)""",
)
parser.add_argument(
    "-o",
    "--outputprefix",
    required=True,
    help="""output file
    prefix for .db files; also used for most auxiliary files""",
)
parser.add_argument(
    "-d",
    "--outputdirectory",
    required=False,
    default=os.getcwd(),
    help="""directory in which all output files will be
    stored; defaults to current working directory (this directory will be
    created if it does not exist, but if the directory cannot be created then
    an error will be raised)""",
)
parser.add_argument(
    "-w",
    "--overwrite",
    required=False,
    default=False,
    action="store_true",
    help="""overwrite output files (if this isn't passed,
    and a non-auxiliary file would need to be overwritten, an error will be
    raised)""",
)
parser.add_argument(
    "-maxn",
    "--maxnodecount",
    required=False,
    default=config.MAXN_DEFAULT,
    type=int,
    help="""connected components with more
    nodes than this value will not be laid out or available for display in the
    viewer interface (default {}, must be at least
    1)""".format(
        config.MAXN_DEFAULT
    ),
)
parser.add_argument(
    "-maxe",
    "--maxedgecount",
    required=False,
    default=config.MAXE_DEFAULT,
    type=int,
    help="""connected components with more
    edges than this value will not be laid out or available for display in the
    viewer interface (default {}, must be at least
    1)""".format(
        config.MAXE_DEFAULT
    ),
)
parser.add_argument(
    "-ub",
    "--userbubblefile",
    required=False,
    help="""file describing pre-identified bubbles in the graph, in the format
    of MetaCarvel's bubbles.txt output: each line of the file is formatted
    as (source ID) (tab) (sink ID) (tab) (all node IDs in the bubble,
    including source and sink IDs, all separated by tabs). See the MetaCarvel
    documentation for more details on this format.""",
)
parser.add_argument(
    "-ubl",
    "--userbubblelabelsused",
    required=False,
    action="store_true",
    default=False,
    help="""use node labels instead of IDs
    in the pre-identified bubbles file specified by -ub""",
)
parser.add_argument(
    "-up",
    "--userpatternfile",
    required=False,
    help="""file
    describing any pre-identified structural patterns in the graph:
    each line of the file is formatted as (pattern type) (tab) (all node IDs
    in the pattern, all separated by tabs). If (pattern type) is "Bubble" or
    "Frayed Rope", then the pattern will be represented in the visualization
    as a Bubble or Frayed Rope, respectively; otherwise, the pattern will
    be represented as a generic "misc. user-specified pattern," and colorized
    accordingly in the visualization.""",
)
parser.add_argument(
    "-upl",
    "--userpatternlabelsused",
    required=False,
    action="store_true",
    default=False,
    help="""use node labels instead of IDs
    in the pre-identified misc. patterns file specified by -up""",
)
parser.add_argument(
    "-spqr",
    "--computespqrdata",
    required=False,
    action="store_true",
    default=False,
    help="""compute data for the SPQR
    "decomposition modes" in MetagenomeScope; necessitates a few additional
    system requirements (see MetagenomeScope's installation instructions
    wiki page for details)""",
)
parser.add_argument(
    "-b",
    "--bicomponentfile",
    required=False,
    help="""file containing bicomponent information for the assembly graph
    (this argument is only used if -spqr is passed, and is not required even in
    that case; the needed files will be generated if -spqr is passed and this
    option is not passed)""",
)
parser.add_argument(
    "-sp",
    "--structuralpatterns",
    required=False,
    default=False,
    action="store_true",
    help="""save .txt files containing node
    information for all structural patterns identified in the graph""",
)
parser.add_argument(
    "-pg",
    "--preservegv",
    required=False,
    action="store_true",
    default=False,
    help="""save all .gv (DOT) files generated for nontrivial
    (i.e. containing more than one node, or at least one edge or node group)
    connected components""",
)
parser.add_argument(
    "-px",
    "--preservexdot",
    required=False,
    default=False,
    action="store_true",
    help="""save all .xdot files generated for nontrivial
    connected components""",
)
parser.add_argument(
    "-nbdf",
    "--nobackfilldotfiles",
    required=False,
    action="store_true",
    default=False,
    help="""produces .gv (DOT) files without
    cluster \"backfilling\" for each nontrivial connected component in the
    graph; use of this argument doesn't impact the .db file produced by this
    script -- it just demonstrates the functionality in layout linearization
    provided by cluster \"backfilling\" """,
)
parser.add_argument(
    "-npdf",
    "--nopatterndotfiles",
    required=False,
    action="store_true",
    default=False,
    help="""produces .gv (DOT) files
    without any structural pattern information embedded; as with -nbdf, this
    doesn't actually impact the .db file -- it just provides a frame of
    reference for the impact clustering can have on dot's layouts""",
)
# parser.add_argument("-au", "--assumeunoriented", required=False, default=False,
#        action="store_true", help="assume that input GML-file graphs are" + \
#            " unoriented (default for GML files is assuming they are" + \
#            " oriented); this option is unfinished")
# parser.add_argument("-ao", "--assumeoriented", required=False, default=False,
#        action="store_true", help="assume that input LastGraph-/GFA-file" + \
#            " graphs are oriented (default for LastGraph/GFA files is" + \
#            " assuming they are unoriented); this option is unfinished")


def run_script(cmdline_args=sys.argv[1:]):
    """Parses command-line arguments, then runs the main script.

    Optionally accepts as input a list of command-line arguments,
    analogous to sys.argv[1:]. It's possible to just specify your own
    list of arguments instead of relying on sys.argv; this is how the
    tests of the preprocessing script work.

    The argument parsing is abstracted to this function in order to avoid
    ArgParse raising errors when this file (collate.py) is imported into
    other code.

    CODELINK: This general paradigm is based on Viktor Kerkez' answer here:
    https://stackoverflow.com/questions/18160078/. Link to Viktor's SO
    profile: https://stackoverflow.com/users/2199958/viktor-kerkez
    """
    # Delay parsing the command-line arguments
    args = parser.parse_args(cmdline_args)
    collate_graph(args)


if __name__ == "__main__":
    run_script()
