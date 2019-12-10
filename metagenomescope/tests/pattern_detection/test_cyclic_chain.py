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
    """Tests that the simple cyclic chain produced above is detected."""
    g = get_simple_cyclic_chain_graph()
    for s in [0, 1, 2, 3]:
        results = AssemblyGraph.is_valid_cyclic_chain(g, s)
        assert results[0]
        assert set(results[1]) == set([0, 1, 2, 3])


def test_isolated_start():
    """Tests that an isolated node and an isolated chain are both not detected
       as cylic chains.
    """
    g = nx.DiGraph()
    g.add_node(0)
    assert not AssemblyGraph.is_valid_cyclic_chain(g, 0)[0]
    g.add_edge(0, 1)
    assert not AssemblyGraph.is_valid_cyclic_chain(g, 0)[0]
    assert not AssemblyGraph.is_valid_cyclic_chain(g, 1)[0]


def test_selfloop():
    """Produces a graph that looks like:

       +---+
       |   |
       V   |
       0 --+

       is a valid cyclic chain!

       Also adds on incoming and outgoing nodes and checks that those don't
       interfere with the detection of the 0 -> 0 cyclic chain:

            +---+
            |   |
            V   |
       1 -> 0 --+
             \
              2
    """
    g = nx.DiGraph()
    g.add_edge(0, 0)

    results = AssemblyGraph.is_valid_cyclic_chain(g, 0)
    assert results[0]
    assert results[1] == [0]

    g.add_edge(1, 0)
    g.add_edge(0, 2)

    results = AssemblyGraph.is_valid_cyclic_chain(g, 0)
    assert results[0]
    assert results[1] == [0]


def test_funky_selfloop():
    """Tests the simple cyclic chain, but now with a self-loop from 0 -> 0.

       The expected behavior in this case (at least at the top level) is that
       we'll classify 0 -> 0 as a cyclic chain, but leave 1, 2, and 3 out of
       this.

       The reason for this is that 0 has an extraneous incoming (and outgoing,
       technically) edge, so it doesn't really fit in in a cyclic chain
       containing other nodes. It all comes down to the simplistic way in which
       we define cyclic chains in the first place; this isn't the "correct"
       behavior so much as it is the behavior you get when you use the rules we
       use for defining patterns.

       +--+-------------+
       |  ^             |
       V  |             |
       0 -+-> 1 -> 2 -> 3
    """

    g = get_simple_cyclic_chain_graph()
    g.add_edge(0, 0)

    # 0 -> 0 is a cyclic chain
    results = AssemblyGraph.is_valid_cyclic_chain(g, 0)
    assert results[0]
    assert results[1] == [0]

    # However, with other starting nodes, you don't find anything -- 0 throws
    # off the detection
    for s in [1, 2, 3]:
        assert not AssemblyGraph.is_valid_cyclic_chain(g, s)[0]


def test_extraneous_outgoing_edge_from_start():
    """Tests that the 0 -> 4 edge here prevents a cyclic chain from being
       detected "starting" at anywhere except for 1.

       I'll be honest, this is kind of weird behavior. It isn't a bug per se --
       we'd still detect this cyclic chain structure assuming the other nodes
       aren't collapsed into something else in the meantime, since we check all
       nodes at the same level as being the start of each type of structure --
       but it is weird nonetheless.

       In the future, I may revise the cyclic chain detection algorithm... or
       remove it entirely. For now, at least, this test should document the
       sometimes-funky behavior of this code.

       +--------------+
       |  4           |
       V /            |
       0 -> 1 -> 2 -> 3
    """
    g = get_simple_cyclic_chain_graph()
    g.add_edge(0, 4)
    for s in [0, 1, 2, 3, 4]:
        print(s)
        results = AssemblyGraph.is_valid_cyclic_chain(g, s)
        if s == 1:
            assert results[0]
        else:
            assert not results[0]


# def test_simple_fr_detection_failures():
#     g = get_simple_fr_graph()
#     for s in [2, 3, 4]:
#         results = AssemblyGraph.is_valid_frayed_rope(g, s)
#         assert not results[0]
#         assert results[1] is None
