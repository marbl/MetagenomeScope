import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_test_path_graph(num_nodes):
    """Returns a "path graph" as a nx DiGraph."""
    return nx.path_graph(num_nodes, nx.DiGraph())


def get_intervening_graph():
    """Returns a graph that contains nodes that "intervene" in many possible
       chains. Looks something like:

          4
         ^
        /
       0 -> 1 -> 2 -> 3
                ^
               /
              5
    """
    g = nx.DiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(0, 4)
    g.add_edge(5, 2)
    return g


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


def test_intervening_paths_harder():
    """Test that checks what chains are found in the "intervening graph."

       Only 2 -> 3 should be detected -- everything else isn't possible due to
       the "intervening" nodes/edges (also, sidenote, writing out "intervening"
       like 5 times here has made it not look like a word at all).
    """
    g = get_intervening_graph()
    # Only one chain can be detected in this graph: 2 -> 3
    for i in set(range(0, 2)) & set(range(3, 6)):
        results = AssemblyGraph.is_valid_chain(g, i)
        assert not results[0] and results[1] is None

    # Check that 2 -> 3 is indeed recognized as a chain
    results = AssemblyGraph.is_valid_chain(g, 2)
    assert results[0] and (results[1] == [2, 3])


def test_intervening_paths_easier():
    """Removes an edge in the "intervening graph" and checks that
       the chain detection's behavior adapts accordingly.

       After this modification, the graph should look like:

          4
         ^
        /
       0 -> 1 -> 2 -> 3

       ... so we should find one chain in this graph, 1 -> 2 -> 3.
    """
    g = get_intervening_graph()
    # Try lopping off the 5 -> 2 edge
    g.remove_edge(5, 2)

    # Now, 1 -> 2 -> 3 should be a valid chain
    # Due to backwards extension, we should be able to start in either 1 or 2
    # and detect the same chain (note the (1, 3) range -- the endpoint, 3, is
    # excluded and therefore not checked)
    for i in range(1, 3):
        results = AssemblyGraph.is_valid_chain(g, i)
        assert results[0] and results[1] == [1, 2, 3]

    # Of course, the other nodes in the graph won't result in chains being
    # detected (3 and 4 have no outgoing nodes, 5 is an "island", 0 has an
    # intervening outgoing edge to 4)
    assert not AssemblyGraph.is_valid_chain(g, 0)[0]
    assert not AssemblyGraph.is_valid_chain(g, 3)[0]
    assert not AssemblyGraph.is_valid_chain(g, 4)[0]
    assert not AssemblyGraph.is_valid_chain(g, 5)[0]
