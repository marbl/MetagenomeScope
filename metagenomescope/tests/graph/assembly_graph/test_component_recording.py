from metagenomescope.graph import AssemblyGraph, PatternStats


def test_component_recording_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    wccs = ag.components
    # Four ccs:
    # 1. 1+, 2+, 3+, Chain of [4-, 5+] (the chain is counted as a single node
    #                                   in the decomposed graph)
    # 2. 1-, 2-, 3-, Chain of [5-, 4+]
    # 3. 6+
    # 4. 6-
    # Components 1/2 and 3/4 have the same number of nodes/edges/patterns, so
    # the precise ordering is arbitrary. We just check that the number of
    # top-level nodes ("real" nodes or collapsed patterns, stored in the 0th
    # position of each 3-tuple in wccs) is correct, and that the total numbers
    # of "real" nodes and edges in the component (stored in the 1st and 2nd
    # position of each 3-tuple) is also correct.
    assert len(wccs) == 4

    for cc_i in (0, 1):
        assert wccs[cc_i].num_total_nodes == 5
        assert wccs[cc_i].num_unsplit_nodes == 5
        assert wccs[cc_i].num_split_nodes == 0
        assert wccs[cc_i].num_full_nodes == 5
        assert wccs[cc_i].num_total_edges == 4
        assert wccs[cc_i].num_real_edges == 4
        assert wccs[cc_i].num_fake_edges == 0
        assert wccs[cc_i].pattern_stats == PatternStats(num_chains=1)
        assert wccs[cc_i].min_name == "1"

    for cc_i in (2, 3):
        assert wccs[cc_i].num_total_nodes == 1
        assert wccs[cc_i].num_unsplit_nodes == 1
        assert wccs[cc_i].num_split_nodes == 0
        assert wccs[cc_i].num_full_nodes == 1
        assert wccs[cc_i].num_total_edges == 0
        assert wccs[cc_i].num_real_edges == 0
        assert wccs[cc_i].num_fake_edges == 0
        assert wccs[cc_i].pattern_stats == PatternStats()
        assert wccs[cc_i].min_name == "6"


def test_component_recording_ecoli_graph():
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    wccs = ag.components

    # Assert that the first component is the big ugly one that contains node 89
    seen_89_in_largest_cc = False
    for node in wccs[0].nodes:
        if node.name == "89":
            seen_89_in_largest_cc = True
            break

    assert seen_89_in_largest_cc

    # Assert that components in the 1-indexed range [6, 11] are all components
    # of a single node and edge (i.e. they are sorted before the
    # other components with just a single node each). This is because these are
    # more "important" than these other components, at least to us. (We used to
    # identify nodes like this as "cyclic chains," but we don't any more.
    # Alas. But they should still be sorted highly due to having an edge!)
    for cc in wccs[5:11]:
        # Check that the component contains just 1 node and 1 edge
        assert cc.num_total_nodes == 1
        assert cc.num_unsplit_nodes == 1
        assert cc.num_split_nodes == 0
        assert cc.num_full_nodes == 1
        assert cc.num_total_edges == 1
        assert cc.num_real_edges == 1
        assert cc.num_fake_edges == 0
        # see below...
        assert cc.total_length == 4

    # Although components [5, 10] all have 1 node and 1 edge, they should be
    # sorted in this exact order. Usually the one with node 76 would come first
    # (because it's longer than 273 and 150), but that actually doesn't matter
    # for this particular test because the version of the E. coli test graph
    # in MetagenomeScope's repo has all the sequences set to 4 bp.
    #
    # So, um, the ties are then broken by the minimum orientationless name in
    # each component. 76 > 273 > 150, since this is lexicographic ordering.
    #
    # (You could maybe make an argument that they should be sorted numerically
    # but I don't really care about that -- mainly I just want the component
    # orderings to be reproducible.)
    assert wccs[5].min_name == "76"
    assert wccs[6].min_name == "76"

    assert wccs[7].min_name == "273"
    assert wccs[8].min_name == "273"

    assert wccs[9].min_name == "150"
    assert wccs[10].min_name == "150"
