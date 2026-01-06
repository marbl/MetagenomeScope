import networkx as nx
from metagenomescope.graph import validators, Node, Edge, Pattern


def get_simple_bp_graph():
    r"""Produces a graph that looks like:

    1 -> 2
      \/
      /\
    3 -> 4
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(1, 4)
    g.add_edge(3, 2)
    g.add_edge(3, 4)
    return g


def check_simple_bp_graph_valid(g, exp_nodes=[1, 2, 3, 4]):
    for s in (1, 3):
        results = validators.is_valid_bipartite(g, s)
        assert results
        assert set(results.node_ids) == set(exp_nodes)
        assert set(results.start_node_ids) == set([1, 3])
        assert set(results.end_node_ids) == set([2, 4])


def test_simple_bipartite_detection():
    g = get_simple_bp_graph()
    check_simple_bp_graph_valid(g)


def test_simple_fr_detection_failures():
    g = get_simple_bp_graph()
    for s in [2, 4]:
        results = validators.is_valid_bipartite(g, s)
        assert not results
        assert results.node_ids == []
        assert results.start_node_ids == []
        assert results.start_node_ids == []


def test_only_1_start_node():
    r"""Tests that a graph that looks like:

     /-> 2
    1
     \-> 4

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.remove_node(3)
    assert not validators.is_valid_bipartite(g, 1)


def test_only_1_end_node():
    r"""Tests that a graph that looks like:

    1 -\
        2
    3 -/

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.remove_node(4)
    assert not validators.is_valid_bipartite(g, 3)
    assert not validators.is_valid_bipartite(g, 1)


def test_extraneous_outgoing_node_from_start_node_ids():
    r"""Tests that a graph that looks like:

      5
     /
    1 -> 2
      \/
      /\
    3 -> 4

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.add_edge(1, 5)
    assert not validators.is_valid_bipartite(g, 1)
    assert not validators.is_valid_bipartite(g, 3)


def test_extraneous_incoming_node_to_end_node_ids():
    r"""Tests that a graph that looks like:

       5
        \
    1 -> 2
      \/
      /\
    3 -> 4

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.add_edge(5, 2)
    assert not validators.is_valid_bipartite(g, 1)
    assert not validators.is_valid_bipartite(g, 3)


def test_end_to_start_cycle():
    r"""Tests that a graph that looks like:

    +----+
    V    |
    1 -> 2
      \/
      /\
    3 -> 4

    ... is not a valid bipartite region.

    I mean we COULD allow this (like we allow frayed ropes to have these kinds
    of end-to-start cycles), but i think that messes with the interpretation
    here.
    """
    g = get_simple_bp_graph()
    g.add_edge(2, 1)
    assert not validators.is_valid_bipartite(g, 1)
    assert not validators.is_valid_bipartite(g, 3)


def test_start_connected():
    r"""Tests that a graph that looks like:

    1 -> 2
    | \/
    V /\
    3 -> 4

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.add_edge(1, 3)
    assert not validators.is_valid_bipartite(g, 1)
    assert not validators.is_valid_bipartite(g, 3)


def test_end_connected():
    r"""Tests that a graph that looks like:

    1 -> 2
      \/ |
      /\ V
    3 -> 4

    ... is not a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.add_edge(2, 4)
    assert not validators.is_valid_bipartite(g, 1)
    assert not validators.is_valid_bipartite(g, 3)


def test_multilayer_start():
    r"""Tests that a graph that looks like:

    1 -> 2<-+
      \/    |
      /\    |
    3 -> 4  |
         |  |
    5----+--+

    ... is a valid bipartite region.
    """
    g = get_simple_bp_graph()
    g.add_edge(5, 4)
    g.add_edge(5, 2)
    assert validators.is_valid_bipartite(g, 1)
    assert validators.is_valid_bipartite(g, 3)
    assert validators.is_valid_bipartite(g, 5)


def test_multilayer_end():
    r"""Tests that a graph that looks like:

      -------+
     /       |
    1 -> 2   |
      \/     |
      /\     |
    3 -> 4   |
     \       |
      \      |
       \     |
         6<--+
    ... is a valid bipartite region. ascii art is hard ok
    """
    g = get_simple_bp_graph()
    g.add_edge(1, 6)
    g.add_edge(3, 6)
    assert validators.is_valid_bipartite(g, 1)
    assert validators.is_valid_bipartite(g, 3)


def test_self_loops_in_bipartite():
    r"""Tries adding self-loops to any of the nodes in a valid bipartite, and
    verify that this prevents this structure from being labeled as bipartite.
    """
    for n in (1, 2, 3, 4):
        g = get_simple_bp_graph()
        g.add_edge(n, n)
        assert not validators.is_valid_bipartite(g, 1)
        assert not validators.is_valid_bipartite(g, 2)
        assert not validators.is_valid_bipartite(g, 3)
        assert not validators.is_valid_bipartite(g, 4)


def test_parallel_edges_in_bipartite():
    r"""Tests that parallel edges are not allowed."""
    for e in ((1, 2), (1, 4), (3, 2), (3, 4)):
        g = get_simple_bp_graph()
        g.add_edge(*e)
        assert not validators.is_valid_bipartite(g, 1)
        assert not validators.is_valid_bipartite(g, 2)
        assert not validators.is_valid_bipartite(g, 3)
        assert not validators.is_valid_bipartite(g, 4)


def test_is_valid_bipartite_tl_only():
    r"""Tests that this function properly disallows bipartites inside others.

    Graph we test:

               5
          +--------+
          | 1 -> 2 |
     6 -> |   \/   |
      \   |   /\   |
       |  | 3 -> 4 |
       |  +--------+
       |/
       /\----\
      /       \
     8 ------> 7


    This is based pretty heavily on test_is_valid_frayed_rope_tl_only() fyi
    """
    child_bp_graph = get_simple_bp_graph()
    child_vr = validators.is_valid_bipartite(child_bp_graph, 1)
    child_nodes = []
    child_edges = []
    assert child_vr
    for n in child_bp_graph.nodes:
        child_nodes.append(Node(n, str(n), {}))
    for i, (n1, n2, key) in enumerate(child_bp_graph.edges, 100):
        child_edges.append(Edge(i, n1, n2, {}))

    child_bp_pattern = Pattern(5, child_vr, child_nodes, child_edges)

    g = nx.MultiDiGraph()
    g.add_edge(6, 5)
    g.add_edge(6, 7)
    g.add_edge(8, 5)
    g.add_edge(8, 7)

    assert validators.is_valid_bipartite(g, 6)
    assert validators.is_valid_bipartite(g, 8)

    # This is still a valid bipartite region if we don't register node 5 as a
    # Pattern
    assert validators.is_valid_bipartite_tl_only(g, 6, {})
    assert validators.is_valid_bipartite_tl_only(g, 8, {})

    # ... But now it isn't
    assert not validators.is_valid_bipartite_tl_only(
        g, 6, {5: child_bp_pattern}
    )
