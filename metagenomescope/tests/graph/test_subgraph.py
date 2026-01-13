from metagenomescope.graph import AssemblyGraph, Subgraph, PatternStats


def test_subgraph_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    sg = Subgraph(
        123,
        "subgraph123",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    assert sg.unique_id == 123
    assert sg.name == "subgraph123"

    assert sg.num_unsplit_nodes == 12
    assert sg.num_split_nodes == 0
    assert sg.num_total_nodes == 12
    assert sg.num_full_nodes == 12

    assert sg.num_real_edges == 8
    assert sg.num_fake_edges == 0
    assert sg.num_total_edges == 8
    assert sg.pattern_stats == PatternStats(num_chains=2)


def test_subgraph_nested_patterns():
    """Tests that nested patterns are processed correctly.

    Previous versions of Subgraph initialization exploded when you used
    nested patterns, due to trying to recursively add in descendants of
    input patterns while ALSO adding all nodes/edges up front. So there
    would be like hundreds of edges unnecessarily lol.

    See https://github.com/marbl/MetagenomeScope/issues/320 wrt the
    attendant pain and suffering that this test should ward us against.
    """
    # see test_bubble_cyclic_chain_identification() in the AsmGraph
    # hierarch decomp tests for a pretty figure of this graph
    # APPRECIATE MY ASCII ART LOL
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )

    sg = Subgraph(
        456,
        "subgraph456",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    assert sg.unique_id == 456
    assert sg.name == "subgraph456"

    assert sg.num_unsplit_nodes == 8
    assert sg.num_split_nodes == 8
    assert sg.num_total_nodes == 16
    assert sg.num_full_nodes == 12

    assert sg.num_real_edges == 16
    assert sg.num_fake_edges == 4
    assert sg.num_total_edges == 20
    assert sg.pattern_stats == PatternStats(num_bubbles=4, num_cyclicchains=1)
