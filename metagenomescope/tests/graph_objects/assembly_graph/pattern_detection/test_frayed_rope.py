import networkx as nx
from metagenomescope.graph_objects import AssemblyGraph


def get_simple_fr_graph():
    r"""Produces a graph that looks like:

    0 -\ /-> 3
        2
    1 -/ \-> 4
    """
    g = nx.DiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)
    return g


def test_simple_fr_detection():
    g = get_simple_fr_graph()
    for s in [0, 1]:
        results = AssemblyGraph.is_valid_frayed_rope(g, s)
        assert results[0]
        assert set(results[1]) == set([0, 1, 2, 3, 4])


def test_simple_fr_detection_failures():
    g = get_simple_fr_graph()
    for s in [2, 3, 4]:
        results = AssemblyGraph.is_valid_frayed_rope(g, s)
        assert not results[0]
        assert results[1] is None


def test_only_1_starting_node():
    r"""Tests that a graph that looks like:

         /-> 3
    0 --2
         \-> 4

     ... is not a valid frayed rope, since it only has 1 "starting" node (2
     only has 1 incoming node).
    """
    g = get_simple_fr_graph()
    g.remove_edge(1, 2)
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]


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
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]
    assert not AssemblyGraph.is_valid_frayed_rope(g, 1)[0]


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
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]


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
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]


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
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]


def test_cyclic_frayed_rope():
    r"""Tests that a graph that looks like:

    +--------+
    |        |
    V        |
    0 -\ /-> 3
        2
    1 -/ \-> 4

     ... is not a valid frayed rope.
    """
    g = get_simple_fr_graph()
    g.add_edge(3, 0)
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]
    assert not AssemblyGraph.is_valid_frayed_rope(g, 1)[0]


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
    assert not AssemblyGraph.is_valid_frayed_rope(g, 0)[0]
    assert not AssemblyGraph.is_valid_frayed_rope(g, 1)[0]
