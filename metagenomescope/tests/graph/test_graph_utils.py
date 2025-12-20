import pytest
import networkx as nx
import metagenomescope.graph.graph_utils as gu
from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import WeirdError


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
