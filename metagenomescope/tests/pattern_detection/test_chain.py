import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_test_path_graph(num_nodes):
    """Returns a "path graph" as a nx DiGraph."""
    return nx.path_graph(num_nodes, nx.DiGraph())


def test_easiest_possible_case():
    """Tests case where the chain is 0 -> 1 -> 2, and the "starting node" used
       is 0.
    """
    g = get_test_path_graph(3)
    results = AssemblyGraph.is_valid_chain(g, 0)

    assert len(results) == 2
    assert results[0]
    assert results[1] == [0, 1, 2]


def test_backwards_extension():
    """Tests case where the chain is 0 -> 1 -> 2, and the "starting node" used
       is 1. In this case, a chain will be detected of 1 -> 2, and -- to verify
       that this chain is "maximally" large -- the chain should be extended
       back up. This should result in a chain being detected that covers the
       full path graph.
    """
    g = get_test_path_graph(3)
    results = AssemblyGraph.is_valid_chain(g, 1)

    assert len(results) == 2
    assert results[0]
    assert results[1] == [0, 1, 2]


def test_easy_no_chain():
    """Tests 0 -> 1 -> 2 case starting at 2. No chain will be found here to
       start off with, so the code won't bother doing the backwards extension
       stuff.
    """
    g = get_test_path_graph(3)
    results = AssemblyGraph.is_valid_chain(g, 2)

    assert len(results) == 2
    assert not results[0]
    assert results[1] is None
