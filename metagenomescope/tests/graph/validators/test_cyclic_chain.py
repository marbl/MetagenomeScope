import networkx as nx
from metagenomescope.graph import validators


def get_simple_cyclic_chain_graph():
    """Produces a graph that looks like:

    +--------------+
    |              |
    V              |
    0 -> 1 -> 2 -> 3
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 0)
    return g


def test_simple_cyclic_chain_detection():
    """Tests that the simple cyclic chain produced above is detected."""
    g = get_simple_cyclic_chain_graph()
    for s in [0, 1, 2, 3]:
        results = validators.is_valid_cyclic_chain(g, s)
        assert results
        assert set(results.nodes) == set([0, 1, 2, 3])
        assert results.start_node_ids == [s]
        if s == 0:
            assert results.end_node_ids == [3]
        else:
            assert results.end_node_ids == [s - 1]


def test_isolated_start():
    """Tests that an isolated node and an isolated chain are both not detected
    as cylic chains.
    """
    g = nx.MultiDiGraph()
    g.add_node(0)
    assert not validators.is_valid_cyclic_chain(g, 0)
    g.add_edge(0, 1)
    assert not validators.is_valid_cyclic_chain(g, 0)
    assert not validators.is_valid_cyclic_chain(g, 1)


def test_selfloop():
    """Produces a graph that looks like:

       +---+
       |   |
       V   |
       0 --+

       is *NOT* a valid cyclic chain. (We used to classify all nodes with
       self-loop edges as cyclic chains, but now we don't because it requires
       us to do some annoying special-casing during the decomposition process.
       Maybe I'll revert this change later, but idk.)

       Also adds on incoming and outgoing nodes and checks that those don't
       interfere:

            +---+
            |   |
            V   |
       1 -> 0 --+
             \
              2
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 0)

    assert not validators.is_valid_cyclic_chain(g, 0)
    g.add_edge(1, 0)
    g.add_edge(0, 2)
    for s in (0, 1, 2):
        assert not validators.is_valid_cyclic_chain(g, s)


def test_funky_selfloop():
    """Tests the simple cyclic chain, but now with a self-loop from 0 -> 0.

    If we allowed self-loop cyclic chains, then we'd just classify 0 -> 0
    as a cyclic chain but leave 1, 2, and 3 out of this. Now, since we disallow
    self-loop cyclic chains, we don't classify anything here as a cyclic chain.

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

    for s in (0, 1, 2, 3):
        assert not validators.is_valid_cyclic_chain(g, 0)


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
        results = validators.is_valid_cyclic_chain(g, s)
        if s == 1:
            assert results
            assert results.nodes == [1, 2, 3, 0]
            assert results.start_node_ids == [1]
            assert results.end_node_ids == [0]
        else:
            assert not results


def test_surrounded_cyclic_chain():
    """Generalized version of test_extraneous_outgoing_edge_from_start():

         +--------------+
         |              |
         V              |
    5 -> 1 -> 2 -> 3 -> 0 -> 4

    The only valid starting node for a cyclic chain here is node 1.
    """

    g = get_simple_cyclic_chain_graph()
    g.add_edge(0, 4)
    g.add_edge(5, 1)
    for s in [0, 1, 2, 3, 4, 5]:
        results = validators.is_valid_cyclic_chain(g, s)
        if s == 1:
            assert results
            assert results.nodes == [1, 2, 3, 0]
            assert results.start_node_ids == [1]
            assert results.end_node_ids == [0]
        else:
            assert not results


def test_simple_whirl():
    r"""Simple case: two nodes, each with an edge to the other.
      __
     /  \
    V    |
    0    1
    |    ^
     \__/
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    results0 = validators.is_valid_cyclic_chain(g, 0)
    assert results0
    assert results0.nodes == [0, 1]
    assert results0.start_node_ids == [0]
    assert results0.end_node_ids == [1]
    results1 = validators.is_valid_cyclic_chain(g, 1)
    assert results1
    assert results1.nodes == [1, 0]
    assert results1.start_node_ids == [1]
    assert results1.end_node_ids == [0]


def test_simple_whirl_intervening_edges():
    r"""Simple case: two nodes, each with an edge to the other.
            __
           /  \
          V    |
    2 --> 0    1 --> 3
          |    ^
           \__/
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    g.add_edge(2, 0)
    g.add_edge(1, 3)
    results0 = validators.is_valid_cyclic_chain(g, 0)
    assert results0
    assert results0.nodes == [0, 1]
    assert results0.start_node_ids == [0]
    assert results0.end_node_ids == [1]
    # Now, 1 is no longer a valid start node for the [0, 1] cyclic chain. This
    # is because 1 has multiple outgoing nodes, so it can't be the "start" of a
    # cyclic chain. dems the breaks
    assert not validators.is_valid_cyclic_chain(g, 1)
    assert not validators.is_valid_cyclic_chain(g, 2)
    assert not validators.is_valid_cyclic_chain(g, 3)


def test_chain_with_parallel_edges_is_not_cyclic_chain():
    """Considers a graph that looks like 1 --> 2 ==> 3 --> 4 --> 5.

    (==> indicates parallel edges in that "diagram.")

    This test case is taken from the chain validator tests. I'm moving it over
    here just to test that, for some perverse reason, the presence of parallel
    edges in a non-cyclic chain doesn't screw things up and make the cyclic
    chain validator think that this structure is a cyclic chain. (Like, I am
    not even sure of how that would happen, but let's be paranoid.)
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(4, 5)

    for s in (1, 2, 3, 4, 5):
        assert not validators.is_valid_cyclic_chain(g, s)


def test_parallel_edges_in_cyclic_chain():
    """Considers a graph that looks like 1 --> 2 ==> 3 --> 4 --> 5.
                                      ^                       |
                                      |                       |
                                      +-----------------------+
    The presence of the bulge from 2 to 3 should disqualify this from being
    a cyclic chain. Collapse the bulge first, then we'll be good!
    """

    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(4, 5)
    g.add_edge(5, 1)

    for s in (1, 2, 3, 4, 5):
        assert not validators.is_valid_cyclic_chain(g, s)


def test_parallel_edge_selfloop():
    """Tests that the presence of parallel edges in a self-loop does not
    somehow make this into a valid cyclic chain."""
    g = nx.MultiDiGraph()
    g.add_edge(0, 0)
    g.add_edge(0, 0)
    assert not validators.is_valid_cyclic_chain(g, 0)


def test_parallel_edge_selfloop_surrounded():
    """Like the above case, but with extra nodes added in."""
    g = nx.MultiDiGraph()
    g.add_edge(0, 0)
    g.add_edge(0, 0)
    g.add_edge(1, 0)
    g.add_edge(0, 2)
    for s in (0, 1, 2):
        assert not validators.is_valid_cyclic_chain(g, s)

    # OK, now this actually would be a valid cyclic chain if not for the 0 -->
    # 0 self-loop. (This is analogous to test_funky_selfloop() above, but the
    # self loop there didn't have parallel edges.)
    # IN ANY CASE the presence of the self-loop (with or without parallel
    # edges) disqualifies there from being a cyclic chain here.
    g.add_edge(2, 1)
    for s in (0, 1, 2):
        assert not validators.is_valid_cyclic_chain(g, s)
