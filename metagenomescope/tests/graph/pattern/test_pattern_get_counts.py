from metagenomescope.graph import AssemblyGraph


def test_get_counts_bubble():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")

    # This graph should contain just a single bubble with 4 nodes and 4 edges
    assert len(ag.bubbles) == 1
    p = ag.bubbles[0]

    assert p.get_counts(ag) == [4, 4, 0]


def test_get_counts_chains():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    # This graph should contain two chains, each with 2 nodes and 1 edge
    assert len(ag.chains) == 2
    for c in ag.chains:
        assert c.get_counts(ag) == [2, 1, 0]
