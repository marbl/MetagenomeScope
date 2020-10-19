from networkx.drawing.nx_agraph import write_dot
from metagenomescope.graph_objects import AssemblyGraph


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

    ...and the following simplifications should happen:

        3
       / \
      1   [Chain] --> 6 ------> [Chain]
     / \ /           /         /
    0   2          11         /
     \            /          /
      \--> [Chain] -> [Chain]

      [Bubble] -> 6 ------> [Chain]
     /                 /         /
    0                11         /
     \              /          /
      \----> [Chain] -> [Chain]
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    ag.hierarchically_identify_patterns()
    # write_dot(ag.decomposed_digraph, "dec.gv")
    # This is with the "maximum" decomposition settings for this test graph.
    assert len(ag.decomposed_digraph.nodes) == 7
    assert len(ag.decomposed_digraph.edges) == 8
    assert len(ag.chains) == 4
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
    """
    raise NotImplementedError


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
        "metagenomescope/tests/input/bubble_chain_test.gml"
    )
    ag.hierarchically_identify_patterns()
    # write_dot(ag.decomposed_digraph, "dec.gv")
    # write_dot(ag.digraph, "digraph.gv")
    # for bub in ag.bubbles:
    #     print(bub)
    assert len(ag.decomposed_digraph.nodes) == 1
    assert len(ag.decomposed_digraph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 4
