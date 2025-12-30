import pytest
from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import GraphParsingError


def test_flye_yeast_lengths_are_ints():
    # just a regression test for when i accidentally left them as floats;
    # see commit 27f3b928
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    assert ag.total_seq_len == 23175100
    assert type(ag.total_seq_len) is int


def test_sanity_checking_already_splitsuffix():
    # https://github.com/marbl/MetagenomeScope/issues/272
    with pytest.raises(GraphParsingError) as ei:
        AssemblyGraph("metagenomescope/tests/input/splitsuffixtest.gml")
    assert str(ei.value) == (
        'A node named "contig-100_3-L" exists in the graph. Nodes cannot '
        'have names that end in "-L" or "-R".'
    )
