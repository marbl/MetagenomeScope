# Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
# Tests the various functions in collate.py.

import sys
from collections import Counter

sys.path.append("graph_collator")
import collate
import config
import utils

def test_reverse_complement():
    assert collate.reverse_complement("") == ""
    assert collate.reverse_complement("A") == "T"
    assert collate.reverse_complement("C") == "G"
    assert collate.reverse_complement("G") == "C"
    assert collate.reverse_complement("T") == "A"
    assert collate.reverse_complement("ACGT") == "ACGT"
    assert collate.reverse_complement("ACCGT") == "ACGGT"
    # This one's an example in the docstring of reverse_complement(), so of
    # course we gotta test it :)
    assert collate.reverse_complement("GCATATA") == "TATATGC"
    # Generate 500 random DNA sequences with lengths in the range [1, 500], and
    # validate their computed reverse complements.
    for i in range(500):
        seq = utils.gen_random_sequence(range(1, 501))
        seq_rc = collate.reverse_complement(seq)
        for b in range(len(seq)):
            assert config.COMPLEMENT[seq[b]] == seq_rc[len(seq_rc) - b - 1]

def test_gc_content():
    assert collate.gc_content("") == (0, 0)
    assert collate.gc_content("A") == (0, 0)
    assert collate.gc_content("C") == (1, 1)
    assert collate.gc_content("G") == (1, 1)
    assert collate.gc_content("T") == (0, 0)
    assert collate.gc_content("ACGT") == (0.5, 2)
    assert collate.gc_content("GCATTCAC") == (0.5, 4)
    assert collate.gc_content("CCTAC") == (0.6, 3)
    for i in range(500):
        seq = utils.gen_random_sequence(range(1, 501))
        gc_content_output = collate.gc_content(seq)
        # Validate output using Python's lovely Counter builtin
        seq_counter = Counter(seq)
        gc_ct = seq_counter["C"] + seq_counter["G"]
        assert float(gc_ct) / len(seq) == gc_content_output[0]
        assert gc_ct == gc_content_output[1]

def test_negate_node_id():
    assert collate.negate_node_id("1") == "-1"
    assert collate.negate_node_id("-3") == "3"
    assert collate.negate_node_id("20") == "-20"
    assert collate.negate_node_id("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert collate.negate_node_id("0") == "-0"
    assert collate.negate_node_id("-0") == "0"
    assert collate.negate_node_id("contig_id_123") == "-contig_id_123"
    assert collate.negate_node_id("-contig_id_123") == "contig_id_123"
    assert collate.negate_node_id("abcdef") == "-abcdef"
    assert collate.negate_node_id("-abcdef") == "abcdef"
