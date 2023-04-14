import networkx as nx
from metagenomescope.graph import validators


def get_simple_fr_graph():
    r"""Produces a graph that looks like:

    0 -\ /-> 3
        2
    1 -/ \-> 4
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)
    return g


def test_simple_fr_detection():
    g = get_simple_fr_graph()
    for s in [0, 1]:
        results = validators.is_valid_frayed_rope(g, s)
        assert results
        assert set(results.nodes) == set([0, 1, 2, 3, 4])


def test_simple_fr_detection_failures():
    g = get_simple_fr_graph()
    for s in [2, 3, 4]:
        results = validators.is_valid_frayed_rope(g, s)
        assert not results
        assert results.nodes == []


def test_only_1_start_node():
    r"""Tests that a graph that looks like:

         /-> 3
    0 --2
         \-> 4

     ... is not a valid frayed rope, since it only has 1 "starting" node (2
     only has 1 incoming node).
    """
    g = get_simple_fr_graph()
    g.remove_edge(1, 2)
    assert not validators.is_valid_frayed_rope(g, 0)


def test_extraneous_outgoing_node_from_start_nodes():
    r"""Tests that a graph that looks like:

      5
     /
    0 -\ /-> 3
        2
    1 -/ \-> 4

     ... is not a valid frayed rope, regardless of if you "start" at 0 or 1.
    """
    g = get_simple_fr_graph()
    g.add_edge(0, 5)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)


def test_nondiverging_middle_node():
    r"""Tests that a graph that looks like:

       0 -\
           2 -> 3
       1 -/

        ... is not a valid frayed rope.
        (It does look like a church rotated 90 degrees, though, I guess?)
    """
    g = get_simple_fr_graph()
    g.remove_edge(2, 4)
    assert not validators.is_valid_frayed_rope(g, 0)


def test_no_outgoing_edges_middle_node():
    r"""Tests that a graph that looks like:

       0 -\
           2
       1 -/

        ... is not a valid frayed rope.
    """
    g = get_simple_fr_graph()
    g.remove_edge(2, 3)
    g.remove_edge(2, 4)
    assert not validators.is_valid_frayed_rope(g, 0)


def test_extraneous_incoming_node_to_end_nodes():
    r"""Tests that a graph that looks like:

              5
               \
       0 -\ /-> 3
           2
       1 -/ \-> 4

        ... is not a valid frayed rope.
    """
    g = get_simple_fr_graph()
    g.add_edge(5, 3)
    assert not validators.is_valid_frayed_rope(g, 0)


def test_end_to_start_cyclic_frayed_rope():
    r"""Tests that a graph that looks like:

    +--------+
    |        |
    V        |
    0 -\ /-> 3
        2
    1 -/ \-> 4

     ... is NOW a valid frayed rope. Wow, character development!
     Note that we only allow cyclic edges from the end node(s) to the start
     node(s): we disallow cyclic edges within the frayed rope, including
     self-loops. Those are tested below.
    """
    g = get_simple_fr_graph()
    g.add_edge(3, 0)
    assert validators.is_valid_frayed_rope(g, 0)
    assert validators.is_valid_frayed_rope(g, 1)

    # ... and if we add another cyclic edge, it's good also, right?
    # (although in practice, we should detect a cyclic simple bubble of
    # [2, 3, 4, 0] rather than detecting a frayed rope here, since the
    # hierarchical decomposition process should afford bubbles higher priority
    # than frayed ropes.)

    g.add_edge(4, 0)
    assert validators.is_valid_frayed_rope(g, 0)
    assert validators.is_valid_frayed_rope(g, 1)


def test_non_end_to_start_cyclic_frayed_rope():
    r"""Tries to add non-end-to-start cyclic edges to a frayed rope, which
    should prevent it from being highlighted as a frayed rope.
    """
    g = get_simple_fr_graph()
    g.add_edge(2, 0)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)

    g = get_simple_fr_graph()
    g.add_edge(3, 2)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)
    g.add_edge(4, 2)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)

    g = get_simple_fr_graph()
    g.add_edge(3, 4)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)


def test_diverges_to_start():
    r"""Tests that a graph that looks like:

    +--------+
    |        |
    V     /--+
    0 -\ /
        2
    1 -/ \-> 4

     ... is not a valid frayed rope.
    """
    g = get_simple_fr_graph()
    g.remove_edge(2, 3)
    g.add_edge(2, 0)
    assert not validators.is_valid_frayed_rope(g, 0)
    assert not validators.is_valid_frayed_rope(g, 1)


def test_self_loops_in_frayed_rope():
    r"""Try adding self-loops to any of the nodes in a valid frayed rope, and
    verify that this prevents this structure from being tagged as a frayed
    rope.
    """
    for n in (0, 1, 2, 3, 4):
        g = get_simple_fr_graph()
        g.add_edge(n, n)
        assert not validators.is_valid_frayed_rope(g, 0)
        assert not validators.is_valid_frayed_rope(g, 1)


def test_parallel_edges_in_frayed_rope():
    r"""Tests that parallel edges in a frayed rope do not prevent detection.

    First, we'll take the below graph and add only one parallel edge at a time
    (so, testing the normal graph but with two 0->2 edges, then with two 1->2
    edges, etc.).

    After that, we'll verify that the big chunky version of this graph, with
    eight edges (one parallel edge for every original edge), is still valid.

    0 -\ /-> 3
        2
    1 -/ \-> 4
    """
    big_chunky_graph = get_simple_fr_graph()

    for e in ((0, 2), (1, 2), (2, 3), (2, 4)):
        g = get_simple_fr_graph()
        g.add_edge(*e)
        assert validators.is_valid_frayed_rope(g, 0)
        assert validators.is_valid_frayed_rope(g, 1)
        big_chunky_graph.add_edge(*e)

    assert validators.is_valid_frayed_rope(big_chunky_graph, 0)
    assert validators.is_valid_frayed_rope(big_chunky_graph, 1)
