from metagenomescope.graph_objects import AssemblyGraph


def test_component_sorting():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    ag.hierarchically_identify_patterns()

    wccs = ag.get_connected_components()
    # Four ccs:
    # 1. 1+, 2+, 3+, Chain of [4-, 5+] (the chain is counted as a single node
    #                                   in the decomposed digraph)
    # 2. 1-, 2-, 3-, Chain of [5-, 4+]
    # 3. 6+
    # 4. 6-
    # Components 1/2 and 3/4 have the same number of nodes/edges/patterns, so
    # the precise ordering is arbitrary. We just check that the number of
    # top-level nodes ("real" nodes or collapsed patterns) is correct.
    assert len(wccs) == 4
    assert len(wccs[0]) == 4
    assert len(wccs[1]) == 4
    assert len(wccs[2]) == 1
    assert len(wccs[3]) == 1

# TODO: Add more comprehensive tests that things like number of nodes within
# all patterns, edge counts, etc. are used in the sorting operation.
