from collections import Counter
import pytest

from metagenomescope import seq_utils
from metagenomescope.tests import utils


def test_gc_content():
    with pytest.raises(ValueError) as ei:
        seq_utils.gc_content("")
    assert "Can't compute the GC content of an empty sequence" in str(ei.value)
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
