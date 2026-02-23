import pytest
import networkx as nx
import metagenomescope.graph.graph_utils as gu
from metagenomescope.graph import AssemblyGraph, Node, Edge
from metagenomescope.graph.validators import ValidationResults
from metagenomescope.errors import WeirdError
from metagenomescope import config


def test_get_only_connecting_edge_uid_simple():
    g = nx.MultiDiGraph()
    g.add_edge(1, 2, uid=5)
    g.add_edge(3, 4, uid=1234)
    assert gu.get_only_connecting_edge_uid(g, 1, 2) == 5
    assert gu.get_only_connecting_edge_uid(g, 3, 4) == 1234


def test_get_only_connecting_edge_uid_not_connected():
    g = nx.MultiDiGraph()
    g.add_edge(1, 2, uid=5)
    g.add_edge(3, 4, uid=1234)
    with pytest.raises(WeirdError) as ei:
        gu.get_only_connecting_edge_uid(g, 1, 4)
    assert str(ei.value) == "0 edges from node ID 1 to node ID 4"


def test_get_only_connecting_edge_uid_multiple_edges():
    g = nx.MultiDiGraph()
    g.add_edge(1, 2, uid=5)
    g.add_edge(1, 2, uid=1234)
    with pytest.raises(WeirdError) as ei:
        gu.get_only_connecting_edge_uid(g, 1, 2)
    assert str(ei.value) == "> 1 edge from node ID 1 to node ID 2"


def test_get_counterpart_parent_id_simple():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    left.parent_id = 5
    right.parent_id = 6
    nodeid2obj = {0: left, 1: right}
    assert gu.get_counterpart_parent_id(0, nodeid2obj) == 6
    assert gu.get_counterpart_parent_id(1, nodeid2obj) == 5


def test_get_counterpart_parent_id_no_parent():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    right.parent_id = 7
    nodeid2obj = {0: left, 1: right}
    assert gu.get_counterpart_parent_id(0, nodeid2obj) == 7
    assert gu.get_counterpart_parent_id(1, nodeid2obj) is None


def test_get_counterpart_parent_id_not_split():
    with pytest.raises(WeirdError) as ei:
        n = Node(0, "N", {})
        gu.get_counterpart_parent_id(0, {0: n})
    assert str(ei.value) == "Node 0 (name: N) is not split?"


def test_get_counterpart_parent_id_not_in_nodeid2obj():
    with pytest.raises(WeirdError) as ei:
        gu.get_counterpart_parent_id(0, {})
    assert str(ei.value) == "ID 0 not in nodeid2obj. Is it a pattern?"

    with pytest.raises(WeirdError) as ei:
        n = Node(0, "N", {})
        gu.get_counterpart_parent_id(1234, {0: n})
    assert str(ei.value) == "ID 1234 not in nodeid2obj. Is it a pattern?"


def test_has_onenode_split_boundaries_onenode_boundaries():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    two = Node(2, "two", {})
    nodeid2obj = {0: left, 1: right, 2: two}

    vr = ValidationResults(config.PT_CHAIN, True, [0, 1, 2], [0], [1])
    assert gu.has_onenode_split_boundaries(vr, nodeid2obj)

    vr2 = ValidationResults(config.PT_CHAIN, True, [0, 1, 2], [2], [1])
    assert not gu.has_onenode_split_boundaries(vr2, nodeid2obj)


def test_has_onenode_split_boundaries_multinode_boundary():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    two = Node(2, "two", {})
    three = Node(3, "three", {})
    nodeid2obj = {0: left, 1: right, 2: two, 3: three}

    # obvs not a valid bipartite but whatever
    vr = ValidationResults(config.PT_BIPARTITE, True, [0, 1, 2], [0, 2], [1])
    assert not gu.has_onenode_split_boundaries(vr, nodeid2obj)

    vr2 = ValidationResults(config.PT_BIPARTITE, True, [0, 1, 2], [0], [1, 2])
    assert not gu.has_onenode_split_boundaries(vr2, nodeid2obj)

    vr3 = ValidationResults(
        config.PT_BIPARTITE, True, [0, 1, 2, 3], [0, 3], [1, 2]
    )
    assert not gu.has_onenode_split_boundaries(vr3, nodeid2obj)


def test_has_onenode_split_boundaries_multinode_boundary_all_split():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    two = Node(2, "two", {})
    three = Node(3, "three", {}, split=config.SPLIT_LEFT, counterpart_node=two)
    nodeid2obj = {0: left, 1: right, 2: two, 3: three}

    vr = ValidationResults(
        config.PT_BIPARTITE, True, [0, 1, 2, 3], [0, 3], [1, 2]
    )
    assert not gu.has_onenode_split_boundaries(vr, nodeid2obj)


def test_check_not_splitting_a_loop():
    x = Node(0, "x", {})
    y = Node(1, "y", {})
    nodeid2obj = {0: x, 1: y}
    gu.check_not_splitting_a_loop(0, 1, nodeid2obj)
    with pytest.raises(WeirdError) as ei:
        gu.check_not_splitting_a_loop(0, 0, nodeid2obj)
    assert str(ei.value) == (
        "Trying to split Node 0 (name: x), which has at least one edge "
        "pointing to itself? This should never happen."
    )


def test_check_and_get_fake_edge_id():
    x = Node(0, "x", {})
    y = Node(1, "y", {})
    e = Edge(9, 0, 1, {}, is_fake=True)
    e2 = Edge(9, 0, 1, {})

    g = nx.MultiDiGraph()
    g.add_edge(0, 1, uid=9)

    assert gu.check_and_get_fake_edge_id(g, x, y, {9: e}) == 9

    with pytest.raises(WeirdError) as ei:
        gu.check_and_get_fake_edge_id(g, x, y, {9: e2})
    assert str(ei.value) == (
        'Edge ID "9" connects Node 0 (name: x) and Node 1 (name: y) but is '
        "not fake?"
    )

    # if we add another edge from 0 -> 1, then now the call to
    # get_only_connecting_edge_uid() should trigger
    g.add_edge(0, 1, uid=10)
    with pytest.raises(WeirdError) as ei:
        gu.check_and_get_fake_edge_id(g, x, y, {9: e})
    assert str(ei.value) == "> 1 edge from node ID 0 to node ID 1"


def test_check_node_split_properly_simple():
    left = Node(0, "N", {})
    right = Node(1, "N", {}, split=config.SPLIT_RIGHT, counterpart_node=left)
    e = Edge(9, 0, 1, {}, is_fake=True)
    g = nx.MultiDiGraph()
    g.add_edge(0, 1, uid=9)
    assert gu.check_node_split_properly(
        g, "N", {"N-L": left, "N-R": right}, {9: e}
    ) == (left, right, 9)


def test_check_node_split_properly_not_split():
    x = Node(0, "x", {})
    y = Node(1, "y", {})
    e = Edge(9, 0, 1, {}, is_fake=True)
    g = nx.MultiDiGraph()
    g.add_edge(0, 1, uid=9)
    with pytest.raises(KeyError) as ei:
        gu.check_node_split_properly(g, "x", {"x": x, "y": y}, {9: e})


def test_validate_multiple_ccs_multiple_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    gu.validate_multiple_ccs(ag)


def test_validate_multiple_ccs_one_cc():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    with pytest.raises(WeirdError) as ei:
        gu.validate_multiple_ccs(ag)
    assert str(ei.value) == "Graph has only a single component"


def test_validate_multiple_ccs_zero_ccs():
    # this should for SURE never happen
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    del ag.components[0]
    with pytest.raises(WeirdError) as ei:
        gu.validate_multiple_ccs(ag)
    assert str(ei.value) == "Graph has < 1 components? Something is busted."


def test_get_treemap_rectangles_empty():
    with pytest.raises(WeirdError) as ei:
        gu.get_treemap_rectangles([], 5)
    assert str(ei.value) == "cc_nums cannot be empty"

    with pytest.raises(WeirdError) as ei:
        gu.get_treemap_rectangles([], 0)
    assert str(ei.value) == "cc_nums cannot be empty"


def test_get_treemap_rectangles_single():
    # NOTE: you gotta use parens otherwise python thinks we are just asserting
    # that the output equals ["#1"] and that the error message to throw if the
    # assert fails is [5]. eep!
    assert gu.get_treemap_rectangles([1], 5) == (["#1"], [5])
    assert gu.get_treemap_rectangles([123456], 5) == (["#123,456"], [5])


def test_get_treemap_rectangles_multi_aggregate():
    assert gu.get_treemap_rectangles([1, 2], 5) == (
        ["#1 \u2013 2 (5-node components)"],
        [10],
    )

    assert gu.get_treemap_rectangles([1, 2, 3], 5) == (
        ["#1 \u2013 3 (5-node components)"],
        [15],
    )

    assert gu.get_treemap_rectangles([3, 4, 5, 6, 7, 8, 9, 10], 67890) == (
        ["#3 \u2013 10 (67,890-node components)"],
        [67890 * 8],
    )


def test_get_treemap_rectangles_multi_discontinuous():
    with pytest.raises(WeirdError) as ei:
        gu.get_treemap_rectangles([1, 3], 5)
    assert str(ei.value) == "Discontinuous size ranks: |1 to 3| != 2"

    with pytest.raises(WeirdError) as ei:
        gu.get_treemap_rectangles([900, 901, 2000, 1999], 30)
    assert str(ei.value) == "Discontinuous size ranks: |900 to 2,000| != 4"


def test_get_treemap_rectangles_multi_no_aggregate():
    assert gu.get_treemap_rectangles([1, 2], 5, aggregate=False) == (
        ["#1", "#2"],
        [5, 5],
    )

    assert gu.get_treemap_rectangles([1, 2, 3], 5, aggregate=False) == (
        ["#1", "#2", "#3"],
        [5, 5, 5],
    )
