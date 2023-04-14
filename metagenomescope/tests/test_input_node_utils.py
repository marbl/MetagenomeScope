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
# Tests the various functions in input_node_utils.py.

from collections import Counter
import pytest

from metagenomescope import input_node_utils, config
from metagenomescope.tests import utils


def test_gc_content():
    with pytest.raises(ValueError) as ei:
        input_node_utils.gc_content("")
    assert "Can't compute the GC content of an empty sequence" in str(ei.value)
    assert input_node_utils.gc_content("A") == (0, 0)
    assert input_node_utils.gc_content("C") == (1, 1)
    assert input_node_utils.gc_content("G") == (1, 1)
    assert input_node_utils.gc_content("T") == (0, 0)
    assert input_node_utils.gc_content("ACGT") == (0.5, 2)
    assert input_node_utils.gc_content("GCATTCAC") == (0.5, 4)
    assert input_node_utils.gc_content("CCTAC") == (0.6, 3)
    for i in range(500):
        seq = utils.gen_random_sequence(range(1, 501))
        gc_content_output = input_node_utils.gc_content(seq)
        # Validate output using Python's lovely Counter builtin
        seq_counter = Counter(seq)
        gc_ct = seq_counter["C"] + seq_counter["G"]
        assert float(gc_ct) / len(seq) == gc_content_output[0]
        assert gc_ct == gc_content_output[1]


def test_negate_node_id():
    with pytest.raises(ValueError) as ei:
        input_node_utils.negate_node_id("")
    assert "Can't negate an empty node ID" in str(ei.value)
    assert input_node_utils.negate_node_id("1") == "-1"
    assert input_node_utils.negate_node_id("-3") == "3"
    assert input_node_utils.negate_node_id("20") == "-20"
    assert input_node_utils.negate_node_id("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert input_node_utils.negate_node_id("0") == "-0"
    assert input_node_utils.negate_node_id("-0") == "0"
    assert input_node_utils.negate_node_id("contig_id_123") == "-contig_id_123"
    assert input_node_utils.negate_node_id("-contig_id_123") == "contig_id_123"
    assert input_node_utils.negate_node_id("abcdef") == "-abcdef"
    assert input_node_utils.negate_node_id("-abcdef") == "abcdef"
