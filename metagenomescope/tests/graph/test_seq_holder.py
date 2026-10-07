import pytest
from metagenomescope.graph import SeqHolder
from metagenomescope.errors import UIError


def test_init():
    s = SeqHolder(
        "metagenomescope/tests/input/sample1.fa",
        ["1", "2", "3", "4", "5", "6"],
    )
    assert len(s) == 6


def test_get_seq():
    s = SeqHolder(
        "metagenomescope/tests/input/sample1.fa",
        ["1", "2", "3", "4", "5", "6"],
    )
    assert s.get_seq("1") == "CGATGCAA"
    assert s.get_seq("-1") == "TTGCATCG"
    assert s.get_seq("6") == "ATGA"
    assert s.get_seq("-6") == "TCAT"


def test_get_seq_missing():
    with pytest.raises(UIError) as ei:
        s = SeqHolder(
            "metagenomescope/tests/input/sample1.fa",
            ["1", "2", "3", "4", "5", "6"],
        )
        s.get_seq("7")
    assert str(ei.value) == 'No sequence named "7" in input FASTA.'
