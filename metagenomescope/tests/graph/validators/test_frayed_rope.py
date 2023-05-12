import networkx as nx
from metagenomescope.graph import validators, Node, Edge, Pattern


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


def check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4]):
    for s in (0, 1):
        results = validators.is_valid_frayed_rope(g, s)
        assert results
        assert set(results.node_ids) == set(exp_nodes)
        assert set(results.start_node_ids) == set([0, 1])
        assert set(results.end_node_ids) == set([3, 4])


def test_simple_fr_detection():
    g = get_simple_fr_graph()
    check_simple_fr_graph_valid(g)


def test_simple_fr_detection_failures():
    g = get_simple_fr_graph()
    for s in [2, 3, 4]:
        results = validators.is_valid_frayed_rope(g, s)
        assert not results
        assert results.node_ids == []
        assert results.start_node_ids == []
        assert results.start_node_ids == []


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


def test_extraneous_outgoing_node_from_start_node_ids():
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


def test_extraneous_incoming_node_to_end_node_ids():
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

     ... is a valid frayed rope. Wow, character development! This test used to
     check that this *wasn't* a valid frayed rope.

     Note that we only allow cyclic edges from the end node(s) to the start
     node(s): we disallow cyclic edges within the frayed rope, including
     self-loops. Those are tested below.
    """
    g = get_simple_fr_graph()
    g.add_edge(3, 0)

    check_simple_fr_graph_valid(g)

    # ... and if we add another cyclic edge, it's good also, right?
    # (although in practice, we should detect a cyclic simple bubble of
    # [2, 3, 4, 0] rather than detecting a frayed rope here, since the
    # hierarchical decomposition process should afford bubbles higher priority
    # than frayed ropes.)

    g.add_edge(4, 0)
    check_simple_fr_graph_valid(g)


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
    r"""Tests that certain parallel edges in a frayed rope are allowed.

    First, we'll take the below graph and add only one parallel edge at a time
    (so, testing the normal graph but with two 0->2 edges, then with two 1->2
    edges, etc.).

    After that, we'll verify that the big chunky version of this graph, with
    eight edges (one parallel edge for every original edge), is still valid.

    0 -\ /-> 3
        2
    1 -/ \-> 4

    NOTE: we don't allow parallel edges in the middle chain of a frayed rope --
    see test_parallel_edges_in_frayed_rope_middle().
    """
    big_chunky_graph = get_simple_fr_graph()

    for e in ((0, 2), (1, 2), (2, 3), (2, 4)):
        g = get_simple_fr_graph()
        g.add_edge(*e)
        check_simple_fr_graph_valid(g)
        big_chunky_graph.add_edge(*e)

    check_simple_fr_graph_valid(big_chunky_graph)
    check_simple_fr_graph_valid(big_chunky_graph)


def test_2_chain_in_frayed_rope():
    r"""Tests that we can detect frayed ropes with long middle paths.

    This graph looks like:

    0 -\       /-> 3
        2 --> 5
    1 -/       \-> 4

    We used to detect this back in the earlier versions of MetagenomeScope;
    then I removed that check, with the rationale that we should automatically
    detect these chains (so then we'd automatically detect these frayed ropes);
    and then I added in the ETFE trimming on chains (which means that we can
    actually have cases where the middle non-branching path of a frayed rope
    won't get collapsed). So, we need to add back support for this, and this
    test verifies that we do actually have this support. Sheesh.
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(5, 3)
    g.add_edge(5, 4)

    check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4, 5])


def test_long_chain_in_frayed_rope():
    r"""Tests that we can detect frayed ropes with longer middle paths!

    The graphs we test here look like:

    0 -\             /-> 3                0 -\                   /-> 3
        2 --> 5 --> 6            and          2 --> 5 --> 6 --> 7
    1 -/             \-> 4                1 -/                   \-> 4

    ... and so on, extending the middle path for a while just to check that
    this works.

    NOTE -- the code here is janky, sorry -- I should ideally make a utility
    function for this, but it's easier and less error-prone to just write it
    out manually.
    """
    # 3 middle nodes
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(5, 6)
    g.add_edge(6, 3)
    g.add_edge(6, 4)
    check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4, 5, 6])

    # 4 middle nodes
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(5, 6)
    g.add_edge(6, 7)
    g.add_edge(7, 3)
    g.add_edge(7, 4)
    check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4, 5, 6, 7])

    # 5 middle nodes
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(5, 6)
    g.add_edge(6, 7)
    g.add_edge(7, 8)
    g.add_edge(8, 3)
    g.add_edge(8, 4)
    check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8])

    # 6 middle nodes
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(5, 6)
    g.add_edge(6, 7)
    g.add_edge(7, 8)
    g.add_edge(8, 9)
    g.add_edge(9, 3)
    g.add_edge(9, 4)
    check_simple_fr_graph_valid(g, exp_nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


def test_parallel_edges_in_frayed_rope_middle():
    r"""Tests that bulges in a frayed rope's middle chain aren't allowed.

    The graph we test here:

    0 -\ /---\       /-> 3
        2     5 --> 6
    1 -/ \---/       \-> 4
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 5)
    g.add_edge(2, 5)
    g.add_edge(5, 6)
    g.add_edge(6, 3)
    g.add_edge(6, 4)

    for s in (0, 1):
        assert not validators.is_valid_frayed_rope(g, s)


def test_is_valid_frayed_rope_tl_only():
    """Tests that this function properly disallows FRs inside other FRs.

    We test this here in a slightly lazy way -- here we don't actually split
    the left and right boundary nodes of the child frayed rope.

    Graph we test:

                9
          +------------+
    5 --> | 0 -\ /-> 3 | --> 7
          |     2      |
    6 --> | 1 -/ \-> 4 | --> 8
          +------------+
    """
    # set up the child pattern
    child_fr_graph = get_simple_fr_graph()
    child_vr = validators.is_valid_frayed_rope(child_fr_graph, 0)
    child_nodes = []
    child_edges = []
    # (this test depends on the normal FR validator working -- if that is
    # broken, bail out immediately)
    assert child_vr
    for n in child_fr_graph.nodes:
        child_nodes.append(Node(n, str(n), {}))
    for i, (n1, n2, key) in enumerate(child_fr_graph.edges, 10):
        child_edges.append(Edge(i, n1, n2, {}))

    child_fr_pattern = Pattern(9, child_vr, child_nodes, child_edges)

    # set up the surrounding graph (after "collapsing" the child frayed
    # rope into a single node)
    g = nx.MultiDiGraph()
    g.add_edge(5, 9)
    g.add_edge(6, 9)
    g.add_edge(9, 7)
    g.add_edge(9, 8)

    assert validators.is_valid_frayed_rope(g, 5)
    assert validators.is_valid_frayed_rope(g, 6)

    # This is still a valid frayed rope if we don't register node 9 as a
    # Pattern
    assert validators.is_valid_frayed_rope_tl_only(g, 5, {})
    assert validators.is_valid_frayed_rope_tl_only(g, 6, {})

    # ... But now it isn't
    assert not validators.is_valid_frayed_rope_tl_only(
        g, 5, {9: child_fr_pattern}
    )


def test_is_valid_frayed_rope_tl_only_other_patterns_ok():
    r"""Tests that other patterns inside frayed ropes (e.g. bulges) are allowed.

    Again, we don't do splitting on the child pattern here for simplicity's
    sake.

    Graph we test:

                9
          +----------+
    5 --> |  /----\  | --> 7
          | 0      1 |
    6 --> |  \----/  | --> 8
          +--------- +
    """
    # set up the bulge graph
    child_bulge_graph = nx.MultiDiGraph()
    child_bulge_graph.add_edge(0, 1)
    child_bulge_graph.add_edge(0, 1)
    child_vr = validators.is_valid_bulge(child_bulge_graph, 0)
    child_nodes = [Node(0, "0", {}), Node(1, "1", {})]
    child_edges = [Edge(2, 0, 1, {}), Edge(3, 0, 1, {})]
    assert child_vr

    bulge_pattern = Pattern(9, child_vr, child_nodes, child_edges)

    # set up the surrounding graph after "collapsing"
    g = nx.MultiDiGraph()
    g.add_edge(5, 9)
    g.add_edge(6, 9)
    g.add_edge(9, 7)
    g.add_edge(9, 8)

    assert validators.is_valid_frayed_rope(g, 5)
    assert validators.is_valid_frayed_rope(g, 6)

    # This is still a valid frayed rope whether or not we register node 9 as a
    # Pattern
    assert validators.is_valid_frayed_rope_tl_only(g, 5, {})
    assert validators.is_valid_frayed_rope_tl_only(g, 6, {})
    assert validators.is_valid_frayed_rope_tl_only(g, 5, {9: bulge_pattern})
    assert validators.is_valid_frayed_rope_tl_only(g, 6, {9: bulge_pattern})
