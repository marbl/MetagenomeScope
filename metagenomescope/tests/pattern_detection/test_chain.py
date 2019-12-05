import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_test_path_graph(num_nodes):
    """Returns a "path graph" as a nx DiGraph."""
    return nx.path_graph(num_nodes, nx.DiGraph())


def test_basic():
    g = get_test_path_graph(3)
    results = AssemblyGraph.is_valid_chain(g, 0)

    assert len(results) == 2
    assert results[0]
    assert results[1] == [0, 1, 2]
