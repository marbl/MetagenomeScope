from metagenomescope.graph import AssemblyGraph


def test_flye_yeast_lengths_are_ints():
    # just a regression test for when i accidentally left them as floats;
    # see commit 27f3b928
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    assert ag.total_seq_len == 23175100
    assert type(ag.total_seq_len) is int
