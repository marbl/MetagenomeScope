import networkx as nx
from metagenomescope.graph import validators


def get_3_node_bubble_graph():
    r"""Returns a graph that looks like:

         /-1-\
        /     \
       0-------2
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(0, 2)
    return g


def get_easy_bubble_graph():
    r"""Returns a graph that looks like:

         /-1-\
        /     \
       0       3
        \     /
         \-2-/

       ... that doesn't look great, but you get the idea ;)
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 3)
    g.add_edge(0, 2)
    g.add_edge(2, 3)
    return g


def test_easy_bubble():
    """Tests that a basic bubble is identified."""
    g = get_easy_bubble_graph()
    results = validators.is_valid_bubble(g, 0)

    assert results
    # Unlike the chain detection tests, we convert results.nodes to a set,
    # and use that for comparison. This is because we don't care about the ID
    # order here (I don't think order really matters in the chain node ID list,
    # either, but it's at least easy to list it out there... whereas here,
    # it's kind of ambiguous which middle paths occur in what order.)
    assert set(results.nodes) == set([0, 1, 2, 3])
    # Check that start and ending nodes identified correctly
    assert results.starting_node == 0
    assert results.ending_node == 3


def test_easy_bubble_fails_when_starting_point_bad():
    """Tests that the same basic bubble as above isn't identified if you don't
    start at "0".
    """
    g = get_easy_bubble_graph()
    for s in [1, 2, 3]:
        results = validators.is_valid_bubble(g, s)
        assert not results
        assert results.nodes == []
        assert results.starting_node is None
        assert results.ending_node is None


def test_easy_3_node_bubble():
    g = get_3_node_bubble_graph()
    results = validators.is_valid_3node_bubble(g, 0)
    assert results
    assert set(results.nodes) == set([0, 1, 2])
    assert results.starting_node == 0
    assert results.ending_node == 2


def test_3node_bubble_func_fails_on_normal_bubble():
    """(It should only detect 3-node bubbles, not normal bubbles.)"""
    g = get_easy_bubble_graph()
    for s in [0, 1, 2, 3]:
        assert not validators.is_valid_3node_bubble(g, s)


def test_3node_bubble_func_doesnt_fail_on_cyclic():
    """As with other cyclic bubble test below, this is up for debate."""
    g = get_3_node_bubble_graph()
    g.add_edge(2, 0)
    for s in [1, 2]:
        assert not validators.is_valid_3node_bubble(g, s)
    vr = validators.is_valid_3node_bubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2]
    assert vr.starting_node == 0
    assert vr.ending_node == 2


def test_3node_bubble_func_fails_on_middle_spur():
    """Tests something looking like

      1----3
     /
    0------2
    """
    g = get_3_node_bubble_graph()
    g.add_edge(1, 3)
    g.remove_edge(1, 2)
    for s in [0, 1, 2, 3]:
        assert not validators.is_valid_3node_bubble(g, s)


def test_3node_bubble_func_fails_on_middle_extra_branch():
    r"""Tests something looking like

      1----3
     / \
    0---2
    """
    g = get_3_node_bubble_graph()
    g.add_edge(1, 3)
    for s in [0, 1, 2, 3]:
        assert not validators.is_valid_3node_bubble(g, s)


def test_3node_bubble_func_fails_on_self_loops():
    r"""Adds loops to each of the three nodes in a simple 3-node bubble, and
    verifies that any of these loops disqualifies this bubble.
    """
    big_chunky_graph = get_3_node_bubble_graph()

    for n in [0, 1, 2]:
        g = get_3_node_bubble_graph()
        g.add_edge(n, n)
        assert not validators.is_valid_3node_bubble(g, 0)
        big_chunky_graph.add_edge(n, n)

    assert not validators.is_valid_3node_bubble(big_chunky_graph, 0)


def test_3node_bubble_func_fails_if_end_points_to_middle():
    r"""Tests something looking like

      1<---+
     /     |
    0---2<-+
    """
    g = get_3_node_bubble_graph()
    g.add_edge(2, 1)
    assert not validators.is_valid_3node_bubble(g, 0)


def test_3node_bubble_func_fails_if_start_equals_end():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    # This should fail due to the "if len(out_node_ids) != 2" check, early on
    # in the validation function
    assert not validators.is_valid_3node_bubble(g, 0)

    g.add_edge(0, 0)
    # This actually won't fail until the "if len(set(composite)) != 3" check
    # wayyy later on in the validation function! That's cool.
    assert not validators.is_valid_3node_bubble(g, 0)


def test_easy_3_node_bubble_func_fails_with_normal_simple_bubble_detection():
    """Tests that is_valid_bubble() doesn't detect 3-node bubbles. Don't
    worry, though, because is_valid_3node_bubble() does!
    """
    g = get_3_node_bubble_graph()
    for s in [1, 2]:
        assert not validators.is_valid_3node_bubble(g, s)


def test_extra_nodes_on_middle():
    r"""Tests that "intervening" edges on/from the middle nodes of a bubble
       causes the bubble to not get detected.

       We test a graph that looks like this -- first where the top edge is
       4 -> 1, and and then when the top edge is 1 -> 4 (both cases should
       cause the bubble to not be detected).

           4
           |
         /-1-\
        /     \
       0       3
        \     /
         \-2-/
    """
    g = get_easy_bubble_graph()
    g.add_edge(4, 1)
    assert not validators.is_valid_bubble(g, 0)
    g = get_easy_bubble_graph()
    g.add_edge(1, 4)
    assert not validators.is_valid_bubble(g, 0)


def test_converge_to_diff_endings():
    r"""Tests that the following graph isn't identified as a bubble:
         /-1--2
        /
       0
        \
         \-3--4
    """
    g = nx.MultiDiGraph()
    nx.add_path(g, [0, 1, 2])
    nx.add_path(g, [0, 3, 4])
    assert not validators.is_valid_bubble(g, 0)


def test_extra_nodes_on_ending():
    r"""Tests that the following graph (starting at 0) isn't identified as a
    bubble, due to the 4 -> 3 edge.

            4
      /-1-\ |
     /     \V
    0       3
     \     /
      \-2-/

    However, flipping this edge to be 3 -> 4 makes this back into a valid
    bubble (since ending nodes can have arbitrary outgoing edges so long as
    they aren't cyclic).
    """
    g = get_easy_bubble_graph()
    g.add_edge(4, 3)
    assert not validators.is_valid_bubble(g, 0)

    # Test that we can get this back to a valid bubble by reversing 4 -> 3 to
    # be 3 -> 4
    g.remove_edge(4, 3)
    g.add_edge(3, 4)
    results = validators.is_valid_bubble(g, 0)
    assert results
    assert set(results.nodes) == set([0, 1, 2, 3])


def test_cyclic_bubbles_ok():
    r"""Tests that the following graph (starting at 0) is identified as a
    bubble, even with the 3 -> 0 edge.

    This may be changed in the future. right now it's allowed.

    +-------+
    |       |
    | /-1-\ |
    V/     \|
    0       3
     \     /
      \-2-/
    """
    g = get_easy_bubble_graph()
    g.add_edge(3, 0)
    assert validators.is_valid_bubble(g, 0)


def test_cyclic_bubble_in_bubble_chain():
    r"""
    Verifies that *just* node 3, in the diagram below, is a valid start node
    for a bubble.

    When we decompose this middle bubble into a single node, it should contain
    the "back edge" from 6 to 3 -- this back edge is what prevents 0 and 6 from
    being valid starting nodes of a bubble right now. This first decomposition
    step will mean that the surrounding 0 and 6's bubbles will then be
    detectable.

               +-------+
         /-1-\ | /-4-\ | /-7-\
        /     \V/     \|/     \
       0       3       6       9
        \     / \     / \     /
         \-2-/   \-5-/   \-8-/
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(0, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(3, 5)
    g.add_edge(4, 6)
    g.add_edge(5, 6)
    g.add_edge(6, 3)
    g.add_edge(6, 7)
    g.add_edge(6, 8)
    g.add_edge(7, 9)
    g.add_edge(8, 9)
    assert validators.is_valid_bubble(g, 3)
    for i in (0, 1, 2, 4, 5, 6, 7, 8, 9):
        assert not validators.is_valid_bubble(g, i)


def test_converges_to_start():
    r"""Tests that the following graph (starting at 0) isn't identified as a
       bubble.

       +-----+
       |     |
       | /-1-+
       V/
       0
       ^\
       | \-2-+
       |     |
       +-----+

       This should fail because, although both paths converge to a common
       point, this common point is the starting node... so the starting and
       ending point in the bubble is the same, and should be explicitly
       disallowed.
    """
    g = nx.MultiDiGraph()
    nx.add_path(g, [0, 1, 0])
    nx.add_path(g, [0, 2, 0])
    assert not validators.is_valid_bubble(g, 0)


def test_bulge_easy():
    g = nx.MultiDiGraph()
    # 2 edges from 0 -> 1
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    assert validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_bulge(g, 1)


def test_bulge_many_edges():
    g = nx.MultiDiGraph()
    # okay, now 3 edges from 0 -> 1
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    assert validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_bulge(g, 1)
    # Can we do 4? Do I hear someone say 4?
    g.add_edge(0, 1)
    assert validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_bulge(g, 1)


def test_bulge_intervening_edges():
    g = nx.MultiDiGraph()
    #  /--\
    # 0    1
    #  \--/^
    #      |
    #      2
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(2, 1)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_bulge(g, 1)
    assert not validators.is_valid_bulge(g, 2)

    g2 = nx.MultiDiGraph()
    #  /--\
    # 0    1
    # |\--/
    # V
    # 2
    g2.add_edge(0, 1)
    g2.add_edge(0, 1)
    g2.add_edge(0, 2)
    assert not validators.is_valid_bulge(g2, 0)
    assert not validators.is_valid_bulge(g2, 1)
    assert not validators.is_valid_bulge(g2, 2)


def test_bulge_linear_chain():
    # just testing uncovered parts of the code...
    # we definitely don't wanna accidentally label chains as bulges
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_bulge(g, 1)


def test_cyclic_bulge():
    def _test_validation_results(vr, nodes=[0, 1]):
        # utility function because i don't wanna write this stuff out five
        # gabillion (aka three) times
        assert len(nodes) == 2
        assert vr
        assert vr.nodes == nodes
        assert vr.starting_node == nodes[0]
        assert vr.ending_node == nodes[1]

    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    _test_validation_results(validators.is_valid_bulge(g, 0))
    assert not validators.is_valid_bulge(g, 1)

    # If we add another edge from 1 -> 0, then now all of a sudden we could
    # use either node as the start of a bulge.
    # You could argue that this should be tagged as something besides a bulge
    # (e.g. should we make a new "cyclic bubble" pattern type...?), but that is
    # a downstream problem.
    g.add_edge(1, 0)
    _test_validation_results(validators.is_valid_bulge(g, 0))
    # If we use 1 as the start of the bulge, then now 1 is the starting node
    # and 0 is the ending node.
    _test_validation_results(validators.is_valid_bulge(g, 1), nodes=[1, 0])


def test_finding_bubble_containing_bulge():
    # This can happen in practice, since we are pretty strict with how we
    # define "bulges" -- not all cases of parallel edges will be turned into
    # bulge patterns.
    # It is kind of ambiguous if we want to allow bulges to remain within
    # (other) bubbles, within chains, within cyclic chains, and within frayed
    # ropes. I think it makes sense to allow them in bubbles and frayed ropes,
    # but *not* within chains / cyclic chains.
    g = get_easy_bubble_graph()
    g.add_edge(0, 1)
    vr = validators.is_valid_bubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2, 3]
    assert vr.starting_node == 0
    assert vr.ending_node == 3


def test_finding_3node_bubble_containing_bulge_from_start_to_middle():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(0, 2)
    # add a bulge between the start node and the middle node
    g.add_edge(0, 1)
    vr = validators.is_valid_3node_bubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2]
    assert vr.starting_node == 0
    assert vr.ending_node == 2


def test_finding_3node_bubble_containing_bulge_from_middle_to_end():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(0, 2)
    # add a bulge between the middle node and the end node
    g.add_edge(1, 2)
    vr = validators.is_valid_3node_bubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2]
    assert vr.starting_node == 0
    assert vr.ending_node == 2

    assert not validators.is_valid_3node_bubble(g, 1)
    assert not validators.is_valid_bulge(g, 1)


def test_finding_3node_bubble_containing_bulge_from_start_to_end():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(0, 2)
    # add a bulge between the start node and the end node
    g.add_edge(0, 2)
    vr = validators.is_valid_3node_bubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2]
    assert vr.starting_node == 0
    assert vr.ending_node == 2

    assert not validators.is_valid_bulge(g, 0)


def test_superbubble_down_edge():
    r"""Tests that the superbubble detection function, and not the other bubble
    detection functions, can identify the following structure as a bubble:

         /-1-\
        /  |  \
       0   |   3
        \  V  /
         \-2-/
    """
    g = get_easy_bubble_graph()
    g.add_edge(1, 2)

    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)

    vr = validators.is_valid_superbubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2, 3]
    assert vr.starting_node == 0
    assert vr.ending_node == 3

    for other_starting_node in [1, 2, 3]:
        assert not validators.is_valid_superbubble(g, other_starting_node)


def test_superbubble_right_edge():
    r"""Tests that the superbubble detection function, and not the other bubble
    detection functions, can identify the following structure as a bubble:

         /-1-\
        /     \
       0------>3
        \     /
         \-2-/
    """
    g = get_easy_bubble_graph()
    g.add_edge(0, 3)

    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)

    vr = validators.is_valid_superbubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2, 3]
    assert vr.starting_node == 0
    assert vr.ending_node == 3

    for other_starting_node in [1, 2, 3]:
        assert not validators.is_valid_superbubble(g, other_starting_node)


def test_superbubble_tip():
    r"""Tests that the following structure isn't a superbubble, due to the 2 ->
    4 tip:

         /-1-\
        /  |  \
       0   |   3
        \  V  /
         \-2-/
           \
            \->4
    """
    g = get_easy_bubble_graph()
    g.add_edge(1, 2)
    g.add_edge(2, 4)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)
    assert not validators.is_valid_superbubble(g, 0)


def test_nested_superbubble():
    r"""Tests the following structure:

         /-1-\
        /  |  \
       0   |   3
      / \  V  / \
     /   \-2-/   \
    4             6
     \           /
      \----5----/

    We should see a superbubble identified starting at 0, even if we use a
    starting node of 4 (due to the find-the-minimal-superbubble logic I added
    in). After we'd decompose this bubble and rerun the validators, we should
    then detect this overall structure as a (simple) bubble.
    """
    g = get_easy_bubble_graph()
    g.add_edge(1, 2)
    g.add_edge(4, 0)
    g.add_edge(4, 5)
    g.add_edge(5, 6)
    g.add_edge(3, 6)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)

    for valid_start in (0, 4):
        vr = validators.is_valid_superbubble(g, valid_start)
        assert vr
        assert vr.nodes == [0, 1, 2, 3]
        assert vr.starting_node == 0
        assert vr.ending_node == 3

    for invalid_start in (1, 2, 3, 5, 6):
        assert not validators.is_valid_superbubble(g, invalid_start)


def test_end_to_start_cyclic_superbubble():
    r"""Tests that the following structure is a valid superbubble:

    +-------+
    |       |
    | /-1-\ |
    V/  |  \|
    0   |   3
     \  V  /
      \-2-/
    """
    g = get_easy_bubble_graph()
    g.add_edge(1, 2)
    g.add_edge(3, 0)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)
    vr = validators.is_valid_superbubble(g, 0)
    assert vr
    assert vr.nodes == [0, 1, 2, 3]
    assert vr.starting_node == 0
    assert vr.ending_node == 3


def test_mid_to_start_cyclic_superbubble():
    r"""Tests that the following structure is not a valid superbubble:

      /-1-\
     /  |  \
    0   |   3
     ^  V  /
      \>2-/

      ... wow, that doesn't look good. UH SO we're gonna add in extra "back
      edges" from 1 to 0, and then from 2 to 0, and test that both of these
      disqualify this from being tagged as a superbubble.
    """
    for mid_node in (1, 2):
        g = get_easy_bubble_graph()
        g.add_edge(1, 2)
        g.add_edge(mid_node, 0)
        assert not validators.is_valid_bulge(g, 0)
        assert not validators.is_valid_3node_bubble(g, 0)
        assert not validators.is_valid_bubble(g, 0)
        assert not validators.is_valid_superbubble(g, 0)


def test_non_end_to_start_cyclic_superbubble():
    r"""Tests that the following structure is not a valid superbubble:

         /-1-\
        /  ^  \
       0   |   3
        \  V  /
         \-2-/

        This is because we only allow (super)bubbles to be cyclic, at least at
        the moment, if the "cyclic" edge goes from the ending node to the
        starting node. But having cycles *within* the bubble complicates
        detection algorithms, and I don't wanna deal with that.
    """
    g = get_easy_bubble_graph()
    g.add_edge(1, 2)
    g.add_edge(2, 1)
    assert not validators.is_valid_bulge(g, 0)
    assert not validators.is_valid_3node_bubble(g, 0)
    assert not validators.is_valid_bubble(g, 0)
    assert not validators.is_valid_superbubble(g, 0)


def test_bubble_with_self_loops():
    r"""Tests that adding self-loops to an easy bubble disqualifies this
    structure as being tagged as a bubble. For example, an "easy" bubble with a
    self-loop on node 1:

          ___
          \ /
         /-1-\
        /     \
       0       3
        \     /
         \-2-/
    """
    for loop_node in (0, 1, 2, 3):
        g = get_easy_bubble_graph()
        g.add_edge(loop_node, loop_node)
        assert not validators.is_valid_bulge(g, 0)
        assert not validators.is_valid_3node_bubble(g, 0)
        assert not validators.is_valid_bubble(g, 0)
        assert not validators.is_valid_superbubble(g, 0)