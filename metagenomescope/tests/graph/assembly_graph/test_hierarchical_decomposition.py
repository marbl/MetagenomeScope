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
    assert len(ag.chains) == 4
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 2
    # no split nodes or fake edges should be left
    assert len(ag.graph.nodes) == 17
    assert len(ag.graph.edges) == 19


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
    # TODO: when we remove "unnecessary" split nodes, node 1 should be merged
    # back.
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
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

    This should be collapsed into a chain that looks like...

    +----------------------------+
    |     +-------+-------+      |
    |     |   2   |   5   |      |
    |     |  / \  |  / \         |
    | 0 ->| 1   4 = 4   7 | -> 8 |
    |     |  \ /  |  \ /  |      |
    |     |   3   |   6   |      |
    |     +-------+-------+      |
    +----------------------------+
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_test.gml")
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 2
    # TODO: when we remove "unnecessary" split nodes, the splits of nodes 1 and
    # 7 should be merged back together. Right now, they are still split up.


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


def test_chain_into_cyclic_chain_merging():
    r"""The input graph looks like

    +------------------+
    |      2           |
    V     / \          |
    0 -> 1   4 -> 5 -> 6
          \ /
           3

    This should turn into a cyclic chain containing a bubble. Nodes 0, 5, and 6
    should just be children of the top-level cyclic chain; we should at first
    identify a chain of 5 -> 6 -> 0, but this chain will then form a cyclic
    chain with the bubble. Creating this cyclic chain will merge the chain's
    contents into the cyclic chain.
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/chain_into_cyclic_chain_merging.gml"
    )
    # TODO: when we remove "unnecessary" split nodes, nodes 1 and 4 should be
    # merged back
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
