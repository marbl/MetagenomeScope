from metagenomescope.graph_objects import AssemblyGraph


def test_simple_hierarch_decomp():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    ag.hierarchically_identify_patterns()
    # This is with the "maximum" decomposition settings for this test graph
    # leaving this test infuriatingly vague for now so that I can change around
    # the way this stuff works in the short term without having to rewrite a
    # gazillion tests (will add details later)
    assert len(ag.decomposed_digraph.nodes) == 7
    assert len(ag.decomposed_digraph.edges) == 8
    assert len(ag.chains) == 4
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
