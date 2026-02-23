import pytest
from metagenomescope import config
from metagenomescope.graph import AssemblyGraph, Node
from metagenomescope.errors import GraphParsingError, WeirdError


def test_flye_yeast_lengths_are_ints():
    # just a regression test for when i accidentally left them as floats;
    # see commit 27f3b928
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    assert ag.total_seq_len == 23175100
    assert type(ag.total_seq_len) is int


def test_flye_yeast_cov_recording():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    assert ag.cov_source == "edge"
    assert ag.cov_field == "cov"
    assert ag.missing_cov_ct == 0
    assert len(ag.covs) == 122
    assert max(ag.covs) == 77078
    assert ag.has_covs
    assert ag.has_covlens


def test_no_edges_metacarvel_gml_cov_recording():
    ag = AssemblyGraph("metagenomescope/tests/input/one.gml")
    assert ag.cov_source is None
    assert ag.cov_field is None
    assert ag.missing_cov_ct == 0
    assert len(ag.covs) == 0
    assert not ag.has_covs
    assert not ag.has_covlens


def test_ordinary_metacarvel_gml_cov_recording():
    ag = AssemblyGraph("metagenomescope/tests/input/aug1_subgraph.gml")
    assert ag.cov_source == "edge"
    assert ag.cov_field == "bsize"
    assert ag.missing_cov_ct == 0
    assert len(ag.covs) == 15
    assert ag.has_covs
    assert not ag.has_covlens


def test_sample_gfa_cov_recording():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.cov_source == "node"
    assert ag.cov_field == "cov"
    assert ag.missing_cov_ct == 10
    assert len(ag.covs) == 2
    assert ag.covs == [4 / 21, 4 / 21]
    assert ag.has_covs
    assert ag.has_covlens


def test_loop_gfa_cov_recording():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    assert ag.cov_source is None
    assert ag.cov_field is None
    assert ag.missing_cov_ct == 0
    assert len(ag.covs) == 0
    assert not ag.has_covs
    assert not ag.has_covlens


def test_sanity_checking_already_splitsuffix():
    # https://github.com/marbl/MetagenomeScope/issues/272
    with pytest.raises(GraphParsingError) as ei:
        AssemblyGraph("metagenomescope/tests/input/splitsuffixtest.gml")
    assert str(ei.value) == (
        'A node named "contig-100_3-L" exists in the graph. Nodes cannot '
        'have names that end in "-L" or "-R".'
    )


def test_sanity_checking_messedup_edge_id():
    with pytest.raises(GraphParsingError) as ei:
        AssemblyGraph("metagenomescope/tests/input/empty_id.gv")
    assert str(ei.value) == (
        'An edge with the ID "123,45" exists in the graph. Edges cannot '
        "have IDs that contain commas."
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
    assert ag.extra_node_attrs == ["length", "cov", "orientation"]


def test_flye_gfa_metadata_integration():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/flye_yeast_noseq.gfa",
        flye_info_fp="metagenomescope/tests/input/flye_yeast_assembly_info.txt",
    )
    assert ag.extra_node_attrs == [
        "length",
        "circ.",
        "cov",
        "mult.",
        "repeat",
        "orientation",
    ]
    assert ag.extra_edge_attrs == []
    assert ag.cov_source == "node"
    assert ag.cov_field == "cov"
    # 27 lines in the .txt file (ignoring scaffolds and the header) times 2 for
    # RC nodes
    assert len(ag.covs) == 54

    # I don't think it is worth the time to write another parser that checks
    # every single segment in the graph, so just hard-code a few knowns:

    # contig 1 is present in the .txt file
    found_contig_1 = False
    # contig 37 is also present in the .txt file, but has mostly different
    # values for things than contig 1
    found_contig_37 = False
    # contig 4 is NOT present in the .txt file! It should get None for most
    # of its metadata
    found_contig_4 = False
    for c in ag.nodeid2obj.values():
        if c.name == "contig_1":
            # lengths should go by the GFA file, NOT by the .txt file
            assert c.data["length"] == 1032844
            assert c.data["cov"] == 90
            assert c.data["circ."] == "-"
            assert c.data["repeat"] == "-"
            assert c.data["mult."] == 1
            found_contig_1 = True
        elif c.name == "contig_37":
            assert c.data["length"] == 5363
            assert c.data["cov"] == 286
            assert c.data["circ."] == "-"
            assert c.data["repeat"] == "+"
            assert c.data["mult."] == 3
            found_contig_37 = True
        elif c.name == "contig_4":
            assert c.data["length"] == 554754
            assert c.data["cov"] is None
            assert c.data["circ."] is None
            assert c.data["repeat"] is None
            assert c.data["mult."] is None
            found_contig_4 = True

    assert found_contig_1
    assert found_contig_37
    assert found_contig_4


def test_sample_gfa_sanity_checking_duplicate_name():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # this should already be run after the decomposition process. just verify
    # that running it again doesn't break
    ag._sanity_check_graph()
    # ok now we get to the fun stuff. Start messing with the graph
    ag.graph.add_node(9999)
    ag.nodeid2obj[9999] = Node(9999, "1", {})
    with pytest.raises(WeirdError) as ei:
        ag._sanity_check_graph()
    assert str(ei.value) == 'Name "1" occurs twice in the graph?'


def test_sample_gfa_sanity_checking_basename_three_times():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    ag.graph.add_node(9999)
    ag.nodeid2obj[9999] = Node(9999, "9999", {})
    ag.nodeid2obj[9999].basename = "2"
    ag.graph.add_node(8888)
    ag.nodeid2obj[8888] = Node(8888, "8888", {})
    ag.nodeid2obj[8888].basename = "2"
    with pytest.raises(WeirdError) as ei:
        ag._sanity_check_graph()
    assert str(ei.value) == 'Basename "2" occurs > 2x in the graph?'


def test_sample_gfa_sanity_checking_lone_split_node():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    ag.graph.add_node(9999)
    c = Node(8888, "9999", {})
    ag.nodeid2obj[9999] = Node(9999, "9999", {}, split=config.SPLIT_LEFT, counterpart_node=c)
    with pytest.raises(WeirdError) as ei:
        ag._sanity_check_graph()
    # we see the basename "9999" just once, but the node with this basename
    # actually is named "9999-L"! oh no!
    # (this is because node c is not in the graph...)
    assert str(ei.value) == 'Basename "9999" not in the graph?'
