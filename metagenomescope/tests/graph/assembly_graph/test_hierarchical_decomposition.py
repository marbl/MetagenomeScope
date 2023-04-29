from metagenomescope.graph import AssemblyGraph


def test_simple_hierarch_decomp():
    r"""I don't know why I called this test "simple", but whatever. The input
        graph looks like

        3
       / \
      1   4 -> 5 ---> 6 -------> 7 -> 14 -> 15 -> 16
     / \ /           /          /
    0   2          11          /
     \            /           /
      8 -> 9 -> 10 -> 12 -> 13

    ...and the following simplifications should happen (not writing every step
    out because that'd take forever, also these drawings ignore node
    splitting):

        3
       / \
      1   [Chain] --> 6 ------> [Chain]
     / \ /           /         /
    0   2          11         /
     \            /          /
      \--> [Chain] -> [Chain]

      [Bub]->[Chain]->6 ------> [Chain]
     /               /         /
    0              11         /
     \            /          /
      \--> [Chain] -> [Chain]

    [Bubble] --> [Chain]

    [Chain]
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    # This is with the "maximum" decomposition settings for this test graph.
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    # TODO: this is currently 5 instead of 4. This is because the rightmost
    # chain (7R -> 14 -> 15 -> 16) is just treated as a child of the top-level
    # chain; when we support chain merging, this rightmost chain should just
    # get merged into the top-level chain, keeping the number of chains at 4.
    # assert len(ag.chains) == 4
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 2


def test_bubble_with_1_in_node():
    r"""The input graph looks like

           2
          / \
    0 -> 1   4
          \ /
           3

    The final decomposition of this should be a chain containing 0 -> [bubble].
    First, we should identify either the bubble ([1,2,3,4]) or the chain ([0,
    1]), and then split 1. Then we identify the chain (if we just identified
    bubble) or the bubble (if we just identified the chain). Then we should
    identify a chain containing the collapsed chain and bubble, at which point
    we should merge "0 -> 1L" into this new top-level chain. Finally, when we
    remove "unneeded" split nodes, we should notice that 1L is at the same
    level as the parent of 1R, so we should merge 1L back into 1R.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test_1_in.gml")
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    # TODO: uncomment when chain merging and unneeded split node merging are
    # added in
    # assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1


def test_bubble_chain_identification():
    r"""The input graph looks like

           2   5
          / \ / \
    0 -> 1   4   7 -> 8
          \ / \ /
           3   6

    First, we should collapse one of the bubbles (order shouldn't impact
    result). Let's say the leftmost bubble is collapsed first.

        +-------+
        |   2   | 5
        |  / \  |/ \
    0 ->| 1   4 |   7 -> 8
        |  \ /  |\ /
        |   3   | 6
        +-------+

    Then a valid bubble would exist where the first bubble is the start node:

        +------+
        |   5  |
        |  / \ |
    0 ->|B1   7|-> 8
        |  \ / |
        |   6  |
        +------+

    However, this is silly, because nothing about the input graph implied any
    sort of hierarchy between these two bubbles. The code should detect that a
    bubble is being used as the start node of this other bubble (or as the end
    node, if the rightmost bubble was detected first), and then handle this
    by duplicating just the shared node between the bubbles:

        +-------+-------+
        |   2   |   5   |
        |  / \  |  / \  |
    0 ->| 1   4 = 4   7 | -> 8
        |  \ /  |  \ /  |
        |   3   |   6   |
        +-------+-------+


    0 -> (Bubble 1) = (Bubble 2) -> 8


        +-------+-------+
        |   2   |   5   |
        |  / \  |  / \  |
    0 ->| 1   4 = 4   7 | -> 8
        |  \ /  |  \ /  |
        |   3   |   6   |
        +-------+-------+

    ... which makes sense.

    Also at some point we should merge everything into a chain going from 0 to
    8. Ideally, chains will support _merging_: so when a chain is created that
    includes another chain at the top-level, that chain will be subsumed into
    the overall chain. So even if 0 -> 1 or 7 -> 8 is created first, the
    resulting graph should be the same.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_test.gml")
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    # TODO: Fix, as described above (everything should be in 1 chain, which
    # contains the two bubbles)
    # assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 2


def test_bubble_cyclic_chain_identification():
    r"""The input graph looks like

    +-----------------+
    |                 |
    |   2   5   8    11
     \ / \ / \ / \  /
      1   4   7   10
     / \ / \ / \ /  \
    |   3   6   9    12
    |                 |
    +-----------------+

    ... that is, it's just a bunch of cyclic bubbles, with the "last" bubble
    in this visual representation (10 -> [11|12] -> 1) being the one that
    has the back-edges drawn.

    TLDR, we should end up with something like

    +=======================================+
    |                                       |
    | +-------+-------+--------+---------+  |
    | |   2   |   5   |   8    |    11   |  |
    | |  / \  |  / \  |  / \   |   /  \  |  |
    +== 1   4 = 4   7 = 7   10 = 10    1 ===+
      |  \ /  |  \ /  |  \ /   |   \  /  |
      |   3   |   6   |   9    |    12   |
      +-------+-------+--------+---------+

    ... where the nodes "shared" by adjacent bubbles (4, 7, 10, 1) are all
    duplicated.
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )
    # write_dot(ag.decomposed_graph, "dec.gv")
    # write_dot(ag.graph, "digraph.gv")
    # for bub in ag.bubbles:
    #     print(bub)
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 4
