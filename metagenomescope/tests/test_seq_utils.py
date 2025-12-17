from collections import Counter
import pytest

from metagenomescope import seq_utils
from metagenomescope.tests import utils
from metagenomescope.errors import WeirdError


def test_gc_content():
    with pytest.raises(WeirdError) as ei:
        seq_utils.gc_content("")
    assert str(ei.value) == "Can't compute the GC content of an empty sequence"
    assert seq_utils.gc_content("A") == (0, 0)
    assert seq_utils.gc_content("C") == (1, 1)
    assert seq_utils.gc_content("G") == (1, 1)
    assert seq_utils.gc_content("T") == (0, 0)
    assert seq_utils.gc_content("ACGT") == (0.5, 2)
    assert seq_utils.gc_content("GCATTCAC") == (0.5, 4)
    assert seq_utils.gc_content("CCTAC") == (0.6, 3)
    for i in range(500):
        seq = utils.gen_random_sequence(range(1, 501))
        gc_content_output = seq_utils.gc_content(seq)
        # Validate output using Python's lovely Counter builtin
        seq_counter = Counter(seq)
        gc_ct = seq_counter["C"] + seq_counter["G"]
        assert float(gc_ct) / len(seq) == gc_content_output[0]
        assert gc_ct == gc_content_output[1]


def test_n50_simple():
    # example from wikipedia:
    # https://en.wikipedia.org/wiki/N50,_L50,_and_related_statistics#N50
    assert seq_utils.n50([2, 3, 4, 5, 6, 7, 8, 9, 10]) == 8


def test_n50_empty():
    with pytest.raises(WeirdError) as ei:
        seq_utils.n50([])
    assert str(ei.value) == "Can't compute the N50 of an empty list"
