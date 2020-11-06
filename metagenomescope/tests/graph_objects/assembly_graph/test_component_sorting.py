from metagenomescope.graph_objects import AssemblyGraph


def test_component_sorting_simple():
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
    # top-level nodes ("real" nodes or collapsed patterns, stored in the 0th
    # position of each 3-tuple in wccs) is correct, and that the total numbers
    # of "real" nodes and edges in the component (stored in the 1st and 2nd
    # position of each 3-tuple) is also correct.
    assert len(wccs) == 4

    assert len(wccs[0][0]) == 4
    assert wccs[0][1] == 5
    assert wccs[0][2] == 4

    assert len(wccs[1][0]) == 4
    assert wccs[1][1] == 5
    assert wccs[1][2] == 4

    assert len(wccs[2][0]) == 1
    assert wccs[2][1] == 1
    assert wccs[2][2] == 0

    assert len(wccs[3][0]) == 1
    assert wccs[3][1] == 1
    assert wccs[3][2] == 0


def test_component_sorting_ecoli_graph():
    ag = AssemblyGraph("metagenomescope/tests/input/E_coli_LastGraph")
    ag.hierarchically_identify_patterns()
    wccs = ag.get_connected_components()

    # Assert that the first component is the big ugly one that contains node 89
    seen_89_in_largest_cc = False
    for node_id in wccs[0][0]:
        if not ag.is_pattern(node_id):
            if ag.decomposed_digraph.nodes[node_id]["name"] == "89":
                seen_89_in_largest_cc = True
                break
        else:
            # Recursively go through all patterns until we find 89
            child_node_ids = []
            pattern_queue = [node_id]
            while len(pattern_queue) > 0:
                pattern = pattern_queue.pop()
                patt_obj = ag.id2pattern[pattern]
                for child_node_id in patt_obj.node_ids:
                    if ag.is_pattern(child_node_id):
                        pattern_queue.append(child_node_id)
                    else:
                        if ag.digraph.nodes[child_node_id]["name"] == "89":
                            seen_89_in_largest_cc = True
                            break
                if seen_89_in_largest_cc:
                    break

    assert seen_89_in_largest_cc

    # Assert that components in the 1-indexed range [6, 11] are all cyclic
    # chains with a single node and edge (i.e. they are sorted before the
    # other components with just a single node each). This is because these are
    # more "important" than these other components, at least to us.
    for wcc_tuple in wccs[5:11]:
        wcc = wcc_tuple[0]
        # Check that the component contains just 1 node at the top level (a
        # cyclic chain pattern)...
        assert len(wcc) == 1
        # ... and just 1 "real" node in full (the one node within the cyclic
        # chain)
        assert wcc_tuple[1] == 1
        # ... and just 1 edge
        assert wcc_tuple[2] == 1
        cyc_id = list(wcc)[0]
        assert ag.is_pattern(cyc_id)
        # This cyclic chain should contain one node and one edge (and no other
        # patterns within itself).
        assert ag.id2pattern[cyc_id].get_counts(ag) == [1, 1, 0]


# TODO: Add more comprehensive tests that things like number of nodes within
# all patterns, edge counts, etc. are used in the sorting operation.
