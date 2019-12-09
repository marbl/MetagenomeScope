import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_simple_cyclic_chain_graph():
    """Produces a graph that looks like:

       +--------------+
       |              |
       V              |
       0 -> 1 -> 2 -> 3
    """
    g = nx.DiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 0)
    return g


def test_simple_cyclic_chain_detection():
    g = get_simple_cyclic_chain_graph()
    for s in [0, 1, 2, 3]:
        results = AssemblyGraph.is_valid_cyclic_chain(g, s)
        assert results[0]
        assert set(results[1]) == set([0, 1, 2, 3])


# def test_simple_fr_detection_failures():
#     g = get_simple_fr_graph()
#     for s in [2, 3, 4]:
#         results = AssemblyGraph.is_valid_frayed_rope(g, s)
#         assert not results[0]
#         assert results[1] is None
