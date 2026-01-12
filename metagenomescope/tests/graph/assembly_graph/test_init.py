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


def test_validate_nonempty_zero_nodes_gml():
    # https://github.com/marbl/MetagenomeScope/issues/279
    with pytest.raises(GraphParsingError) as ei:
        AssemblyGraph("metagenomescope/tests/input/zero.gml")
    assert str(ei.value) == "Graph has 0 nodes."


def test_validate_nonempty_zero_nodes_dot():
    # https://github.com/marbl/MetagenomeScope/issues/279
    with pytest.raises(GraphParsingError) as ei:
        AssemblyGraph("metagenomescope/tests/input/zero.gv")
    # this is actually caught by the DOT parser! which is also fine.
    # the validate_nonempty() thing exists as a last resort.
    assert str(ei.value) == "DOT-format graph contains 0 edges."


def test_validate_nonempty_one_node_gml():
    # this is okay
    ag = AssemblyGraph("metagenomescope/tests/input/one.gml")
    assert ag.node_ct == 1
    assert ag.edge_ct == 0


def test_noseq_gfa_has_no_gc_contents():
    ag = AssemblyGraph("metagenomescope/tests/input/sheepgut_g1217.gfa")
    assert ag.extra_node_attrs == ["length", "orientation"]
