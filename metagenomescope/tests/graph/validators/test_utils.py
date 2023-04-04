import pytest
import networkx as nx
from metagenomescope.graph import validators
from metagenomescope.errors import WeirdError


def test_verify_node_in_graph():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    validators.verify_node_in_graph(g, 0)
    validators.verify_node_in_graph(g, 1)
    with pytest.raises(WeirdError) as ei:
        validators.verify_node_in_graph(g, 2)
    assert "Node 2 is not present in the graph's nodes?" in str(ei.value)
