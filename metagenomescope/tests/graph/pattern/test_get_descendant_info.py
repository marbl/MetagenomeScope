from metagenomescope.graph import AssemblyGraph, PatternStats


def test_get_descendant_info_bubble():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")
    # This graph should contain just a single bubble with 4 nodes and 4 edges
    assert len(ag.bubbles) == 1
    p = ag.bubbles[0]
    nodes, edges, patts, patt_stats = p.get_descendant_info()
    assert len(nodes) == 4
    assert sorted([n.name for n in nodes]) == [
        "contig-100_1",
        "contig-100_2",
        "contig-100_3",
        "contig-100_4",
    ]
    assert len(edges) == 4
    assert len(patts) == 1
    assert patt_stats == PatternStats(num_bubbles=1)


def test_get_descendant_info_chain():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # This graph should contain two chains, each with 2 nodes and 1 edge
    assert len(ag.chains) == 2
    for p in ag.chains:
        nodes, edges, patts, patt_stats = p.get_descendant_info()
        assert len(nodes) == 2
        assert len(edges) == 1
        assert len(patts) == 1
        assert patt_stats == PatternStats(num_chains=1)


def test_get_descendant_info_bubble_cyclic_chain():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )
    # This graph should contain 1 cyclic chain, beneath which are four bubbles
    assert len(ag.cyclic_chains) == 1
    p = ag.cyclic_chains[0]
    nodes, edges, patts, patt_stats = p.get_descendant_info()
    assert len(nodes) == 16
    assert len(edges) == 20
    assert len(patts) == 5
    assert patt_stats == PatternStats(num_bubbles=4, num_cyclicchains=1)
