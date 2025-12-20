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
