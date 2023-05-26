import os
import tempfile
import networkx as nx
from copy import deepcopy
from metagenomescope.graph import AssemblyGraph


def nx2gml(g):
    """Writes a nx.MultiDiGraph to a MetaCarvel-style GML file.

    ... because making a separate GML file for every one of these tests is
    getting kind of annoying"""
    gc = deepcopy(g)
    for n in gc.nodes:
        gc.nodes[n]["orientation"] = "FOW"
        gc.nodes[n]["length"] = 100
    for e in gc.edges(keys=True):
        gc.edges[e]["orientation"] = "EB"
        gc.edges[e]["mean"] = 100
        gc.edges[e]["stdev"] = 50
        gc.edges[e]["bsize"] = 5
    filehandle, filename = tempfile.mkstemp(suffix=".gml")
    nx.write_gml(gc, filename)
    return filehandle, filename


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
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
    # no split nodes or fake edges should be left
    assert len(ag.graph.nodes) == 5
    assert len(ag.graph.edges) == 5


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
    # when we remove "unnecessary" split nodes, the splits of nodes 1 and
    # 7 should be merged back together.
    node_names = []
    for ni in ag.graph.nodes:
        node_names.append(ag.nodeid2obj[ni].name)
    assert sorted(node_names) == [
        "0",
        "1",
        "2",
        "3",
        "4-L",
        "4-R",
        "5",
        "6",
        "7",
        "8",
    ]
    edges = []
    fake4_seen = False
    for src, tgt, d in ag.graph.edges(data=True):
        obj = ag.edgeid2obj[d["uid"]]
        assert src == obj.new_src_id
        assert tgt == obj.new_tgt_id
        sn = ag.nodeid2obj[src].name
        tn = ag.nodeid2obj[tgt].name
        edges.append((sn, tn))
        if sn == "4-L" and tn == "4-R":
            fake4_seen = True
            assert obj.is_fake
        else:
            assert not obj.is_fake
    assert fake4_seen
    assert sorted(edges) == [
        ("0", "1"),
        ("1", "2"),
        ("1", "3"),
        ("2", "4-L"),
        ("3", "4-L"),
        ("4-L", "4-R"),
        ("4-R", "5"),
        ("4-R", "6"),
        ("5", "7"),
        ("6", "7"),
        ("7", "8"),
    ]


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
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 4
    assert len(ag.graph.nodes) == 16
    assert len(ag.graph.edges) == 20


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
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
    # when we remove "unnecessary" split nodes, nodes 1 and 4 should no longer
    # be split
    assert len(ag.graph.nodes) == 7
    assert len(ag.graph.edges) == 8


def test_multiple_frayed_ropes():
    r"""The input graph looks like

    0   3
     \ /
      1
     / \
    2   4   7
         \ /
          5
         / \
        6   8

    ... We should see both of these frayed ropes identified, but -- due to our
    use of frayed rope border splitting -- these frayed ropes should be
    separate structures.
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(2, 1)
    g.add_edge(1, 3)
    g.add_edge(1, 4)

    g.add_edge(4, 5)
    g.add_edge(6, 5)
    g.add_edge(5, 7)
    g.add_edge(5, 8)

    fh, fn = nx2gml(g)
    # doing the gist of what run_tempfile_test() does -- avoids cluttering
    # filesystem with test GMLs
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 2
        assert len(ag.decomposed_graph.edges) == 1
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 2
        assert len(ag.bubbles) == 0
        assert len(ag.graph.nodes) == 10
        assert len(ag.graph.edges) == 9
    finally:
        os.close(fh)
        os.unlink(fn)


def test_chain_Y_aug1_subgraph():
    r"""The input graph looks like

                                             /-> 9 -> 10
    0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8
                                             \-> 11 -> 12 -> 13 -> 14 -> 15

    There was previously a bug that messed up how edges were routed during node
    splitting (that would break graphs like this). This test ensures that this
    bug doesn't pop up again.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/aug1_subgraph.gml")
    assert len(ag.decomposed_graph.nodes) == 3
    assert len(ag.decomposed_graph.edges) == 2
    assert len(ag.chains) == 3
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 0
    # no split nodes or fake edges should be left
    assert len(ag.graph.nodes) == 16
    assert len(ag.graph.edges) == 15


def test_chain_backwards_Y():
    r"""The input graph looks like

    0 -> 1 -> 2\
                3 -> 4 -> 5 -> 6
    7 -> 8 -> 9/

    The opposite of the test_chain_Y...() test.
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)

    g.add_edge(7, 8)
    g.add_edge(8, 9)
    g.add_edge(9, 3)

    g.add_edge(3, 4)
    g.add_edge(4, 5)
    g.add_edge(5, 6)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 3
        assert len(ag.decomposed_graph.edges) == 2
        assert len(ag.chains) == 3
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 0
        assert len(ag.graph.nodes) == 10
        assert len(ag.graph.edges) == 9
    finally:
        os.close(fh)
        os.unlink(fn)


def test_multiedges_between_frayed_ropes():
    r"""The input graph looks like

    0   3 --> 5   8
     \ /  \ /  \ /
      2    /    7
     / \  / \  / \
    1   4 --> 6   9
         \
          10
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)

    g.add_edge(3, 5)
    g.add_edge(3, 6)
    g.add_edge(4, 5)
    g.add_edge(4, 6)

    g.add_edge(5, 7)
    g.add_edge(6, 7)
    g.add_edge(7, 8)
    g.add_edge(7, 9)

    # this edge is just here to prevent us identifying a big bubble between 2
    # and 7
    g.add_edge(4, 10)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 3
        assert len(ag.decomposed_graph.edges) == 5
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 2
        assert len(ag.bubbles) == 0
        # the boundary nodes of both frayed ropes should not be split after
        # decomposition is finished
        assert len(ag.graph.nodes) == 11
        assert len(ag.graph.edges) == 13
    finally:
        os.close(fh)
        os.unlink(fn)


def test_multiple_shared_boundaries_frayed_ropes():
    r"""The input graph looks like

    +---+
    |   |
    V   |
    0   3   8
     \ / \ /
      2   7
     / \ / \
    1   4   9
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)

    g.add_edge(3, 7)
    g.add_edge(4, 7)
    # again, this edge (now cyclic) just makes sure we identify this as 2
    # frayed ropes, not a bubble
    g.add_edge(3, 0)

    g.add_edge(7, 8)
    g.add_edge(7, 9)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 2
        assert len(ag.decomposed_graph.edges) == 2
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 2
        assert len(ag.bubbles) == 0
        # Nodes 3 and 4 should both be split
        assert len(ag.graph.nodes) == 10
        assert len(ag.graph.edges) == 11
    finally:
        os.close(fh)
        os.unlink(fn)


def test_no_patterns():
    r"""The input graph looks like

           2
          / \
    0 -> 1   4
          \ /
           3

    ... but if we set patterns=False when creating the AssemblyGraph, we
    shouldn't identify any patterns.
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_test_1_in.gml", patterns=False
    )
    assert sorted(ag.decomposed_graph.nodes) == sorted([0, 1, 2, 3, 4])
    assert len(ag.decomposed_graph.edges) == 5
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 0
    assert sorted(ag.graph.nodes) == sorted([0, 1, 2, 3, 4])
    assert len(ag.graph.edges) == 5


def test_chr21mat_split_siblings_merged():
    r"""The input graph looks like


    +------------------------------------------------------------+
    |                                                            |
    V                 /--\                   /--\                |
    2213790 -> 5308795    -1005641 -> 2387648    248316 -> 6585325 -> -3300458
                      \--/                   \--/

    We should ideally identify this as a chain (containing a cyclic chain (from
    2213790 to 6585325, containing two bulges) and -3300458. Additionally, *no
    nodes should be split after decomposition finishes* -- a bug in
    MetagenomeScope right was causing 6585325 and 2213790 to remain split,
    even though they shouldn't be. (This was due to both of these nodes' splits
    (658-L and 658-R, and 221-L and 221-R, being siblings -- which my code
    initially didn't expect.)

    So this is what they call a "regression test," as i understand it. now i
    don't know much in this crazy world, but uhhh let's avoid this recurring :P
    """
    ag = AssemblyGraph("metagenomescope/tests/input/chr21mat_subgraph.gv")
    # outermost node is a chain
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 2

    # Nodes should not be split
    assert len(ag.graph.nodes) == 7
    assert set([n.name for n in ag.nodeid2obj.values()]) == {
        "2213790",
        "5308795",
        "-1005641",
        "2387648",
        "248316",
        "6585325",
        "-3300458",
    }
    for n in ag.nodeid2obj.values():
        assert n.is_not_split()

    assert len(ag.graph.edges) == 9
    # extremely lazy way to check that the edges in the graph are what we
    # expect. tbh i forgot that the edges in ag.graph would use node unique ids
    # so that's why this ugly list comprehension that converts ids to names
    # exists, sorry for inflicting it upon your eyes
    #
    # e[2] is the edge key in networkx when you use ag.graph.edges btw (i am a
    # very cool person who will definitely remember how nx multidigraphs work
    # two weeks from now when i have to look at this code again)
    assert set(
        [
            (ag.nodeid2obj[e[0]].name, ag.nodeid2obj[e[1]].name, e[2])
            for e in ag.graph.edges
        ]
    ) == {
        ("2213790", "5308795", 0),
        ("5308795", "-1005641", 0),
        ("5308795", "-1005641", 1),
        ("-1005641", "2387648", 0),
        ("2387648", "248316", 0),
        ("2387648", "248316", 1),
        ("248316", "6585325", 0),
        ("6585325", "2213790", 0),
        ("6585325", "-3300458", 0),
    }
