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
# This file contains some utility functions that should help simplify the
# process of creating tests for MetagenomeScope's preprocessing script.

import random
from metagenomescope.graph import AssemblyGraph


def gen_random_sequence(possible_lengths):
    """Generates a random DNA sequence with a length in the provided list."""

    seq_len = random.choice(possible_lengths)
    alphabet = "ACGT"
    seq = ""
    i = 0
    while i < seq_len:
        seq += random.choice(alphabet)
        i += 1
    return seq


def get_cycle_with_tip_data():
    """Returns info about a graph 1 -> 2 -> 3, with a back edge 2 -> 1.

    This is useful in testing layout, and I guess there are multiple
    levels through which the layout process gets triggered (by calling
    Layout(), by calling Subgraph.to_cyjs(), ...) So I guess we can put this
    here so we can use it in various places.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/cycle_with_tip.gfa")

    # one component has nodes {1, 2, 3}; the other has {-3, -2, -1}.
    # we just care about the one with the positive node names here.
    assert len(ag.components) == 2
    nrccnums = ag.get_nr_cc_nums()
    assert len(nrccnums) == 1
    cc = ag.components[list(nrccnums)[0] - 1]

    # find node objects
    assert len(cc.nodes) == 3
    n1 = None
    n2 = None
    n3 = None
    for n in cc.nodes:
        assert n.name in ("1", "2", "3")
        if n.name == "1":
            n1 = n
        elif n.name == "2":
            n2 = n
        else:
            n3 = n
    assert n1 is not None
    assert n2 is not None
    assert n3 is not None

    return ag, cc, n1, n2, n3
