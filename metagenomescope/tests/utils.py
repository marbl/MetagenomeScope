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
