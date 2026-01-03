from metagenomescope.graph import AssemblyGraph


def test_get_neighborhood_zero():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id_list = ag.get_node_ids("1")
    only_id = id_list[0]
    subgraph, subgraph_node_ids = ag.get_neighborhood(id_list, 0)
    assert subgraph_node_ids == {only_id}
    assert len(subgraph.edges) == 0
    assert len(subgraph.nodes) == 1
    assert list(subgraph.nodes) == [only_id]


def test_get_neighborhood_one():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id1 = ag.get_node_ids("1")[0]
    id2 = ag.get_node_ids("2")[0]
    ids = {id1, id2}
    subgraph, subgraph_node_ids = ag.get_neighborhood([id1], 1)
    assert subgraph_node_ids == ids
    assert len(subgraph.edges) == 1
    assert len(subgraph.nodes) == 2
    assert sorted(subgraph.nodes) == sorted(ids)


def test_get_neighborhood_two():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id1 = ag.get_node_ids("1")[0]
    id2 = ag.get_node_ids("2")[0]
    id3 = ag.get_node_ids("3")[0]
    ids = {id1, id2, id3}
    subgraph, subgraph_node_ids = ag.get_neighborhood([id1], 2)
    # Now we are testing that the search moves "backwards". This
    # subgraph looks like 1 -> 2, 3 -> 2 -- test that we can reach
    # 3 from 1
    assert subgraph_node_ids == ids
    assert len(subgraph.edges) == 2
    assert len(subgraph.nodes) == 3
    assert sorted(subgraph.nodes) == sorted(ids)


def check_sample1_subgraph_entire_component(
    ag, all_node_ids_in_cc, snodeids, sedgeids
):
    def id2name(i):
        return ag.nodeid2obj[i].name

    assert list(snodeids) == all_node_ids_in_cc

    assert len(sedgeids) == 4
    seen_edges = []
    for eid in sedgeids:
        seen_edges.append(
            (
                id2name(ag.edgeid2obj[eid].new_src_id),
                id2name(ag.edgeid2obj[eid].new_tgt_id),
            )
        )

    assert sorted(seen_edges) == [
        ("-4", "5"),
        ("1", "2"),
        ("3", "-4"),
        ("3", "2"),
    ]


def test_get_ids_in_neighborhood_entire_component():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    all_node_ids_in_cc = ag.get_node_ids("1,2,3,-4,5")

    snodeids, sedgeids, spattids = ag.get_ids_in_neighborhood(
        all_node_ids_in_cc, 100, True
    )
    check_sample1_subgraph_entire_component(
        ag, all_node_ids_in_cc, snodeids, sedgeids
    )

    assert len(spattids) == 1
    assert sorted(n.name for n in ag.pattid2obj[list(spattids)[0]].nodes) == [
        "-4",
        "5",
    ]


def test_get_ids_in_neighborhood_entire_component_dont_incl_patterns():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    all_node_ids_in_cc = ag.get_node_ids("1,2,3,-4,5")

    snodeids, sedgeids, spattids = ag.get_ids_in_neighborhood(
        all_node_ids_in_cc, 100, False
    )
    check_sample1_subgraph_entire_component(
        ag, all_node_ids_in_cc, snodeids, sedgeids
    )

    assert len(spattids) == 0
