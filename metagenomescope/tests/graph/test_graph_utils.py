import pytest
import networkx as nx
import metagenomescope.graph.graph_utils as gu
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
