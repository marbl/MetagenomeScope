import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_test_path_graph(num_nodes):
    """Returns a "path graph" as a nx DiGraph."""
    return nx.path_graph(num_nodes, nx.DiGraph())


def get_3_node_bubble_graph():
    """Returns a graph that looks like:

         /-1-\
        /     \
       0-------2
    """
    g = nx.DiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(0, 2)
    return g


def get_easy_bubble_graph():
    """Returns a graph that looks like:

         /-1-\
        /     \
       0       3
        \     /
         \-2-/

       ... that doesn't look great, but you get the idea ;)
    """
    g = nx.DiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 3)
    g.add_edge(0, 2)
    g.add_edge(2, 3)
    return g


def test_easy_bubble():
    """Tests that a basic bubble is identified."""
    g = get_easy_bubble_graph()
    results = AssemblyGraph.is_valid_bubble(g, 0)

    assert len(results) == 2
    assert results[0]
    # Unlike the chain detection tests, we don't look at results[1] (the list
    # of IDs in the pattern) directly. Instead, we convert it to a set, and
    # compare using that. This is because we don't care about the ID order
    # here (I don't think order really matters in the chain node ID list,
    # either, but it's at least easy to list it out there... whereas here,
    # it's kind of amibiguous which middle paths occur in what order.)
    assert set(results[1]) == set([0, 1, 2, 3])


def test_easy_bubble_fails_when_starting_point_bad():
    """Tests that the same basic bubble as above isn't identified if you don't
       start at "0".
    """
    g = get_easy_bubble_graph()
    for s in [1, 2, 3]:
        results = AssemblyGraph.is_valid_bubble(g, s)
        assert not results[0]
        assert results[1] is None


# NOTE: This test will fail because the bubble-finding code doesn't yet work
# with bubbles where there's a direct edge btwn. the start and end node. If we
# ever implement support for that type of bubble directly in MgSc, this test
# should be useful.
# def test_easy_3_node_bubble():
#     g = get_3_node_bubble_graph()
#     results = AssemblyGraph.is_valid_bubble(g, 0)
#     assert results[0] and set(results[1]) == set([0, 1, 2])


def test_easy_3_node_bubble_fails():
    """...since we don't support these. Yet."""
    g = get_3_node_bubble_graph()
    for s in [1, 2]:
        assert not AssemblyGraph.is_valid_bubble(g, s)[0]
