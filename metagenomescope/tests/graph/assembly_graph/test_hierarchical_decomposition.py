import os
import tempfile
import networkx as nx
from copy import deepcopy
from metagenomescope.graph import AssemblyGraph
from metagenomescope.parsers import parse_dot


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


def _check_ag_topology_matches_gv(ag, gv_fn):
    """This assumes that all nodes in the AssemblyGraph are not split."""
    for n in ag.nodeid2obj.values():
        assert n.is_not_split()

    # Verify that the topology of ag.graph matches the input (it should be an
    # exact match -- no split nodes or fake edges should remain after
    # hierarchical decomposition in this graph)
    correct_graph = parse_dot(gv_fn)
    assert len(correct_graph.nodes) == len(ag.graph.nodes)
    assert len(correct_graph.nodes) == len(ag.nodeid2obj)
    assert len(correct_graph.edges) == len(ag.graph.edges)
    assert len(correct_graph.edges) == len(ag.edgeid2obj)
    # Verify that the out edges of each node in ag.graph match the
    # corresponding out edges in correct_graph. Note that
    # nx.MultiDiGraph.out_edges() includes multi-edges, so this is safe.
    for n in ag.graph:
        n_name = ag.nodeid2obj[n].name
        assert n_name in correct_graph.nodes
        ag_targets = [
            ag.nodeid2obj[oe[1]].name for oe in ag.graph.out_edges(n)
        ]
        cg_targets = [oe[1] for oe in correct_graph.out_edges(n_name)]
        assert set(ag_targets) == set(cg_targets)

    # Verify that the Edge objects in this graph also match the input perfectly
    cg_edges = list(correct_graph.edges(data=True))
    for e in ag.edgeid2obj.values():
        src_name = ag.nodeid2obj[e.new_src_id].name
        tgt_name = ag.nodeid2obj[e.new_tgt_id].name
        e_tuple = (src_name, tgt_name, e.data)
        # This is inefficient and gross but cg_edges should be a small list so
        # this works well enough
        assert cg_edges.count(e_tuple) == 1
        cg_edges.remove(e_tuple)
    assert len(cg_edges) == 0


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

    If we were to allow "end-to-start" cyclic frayed ropes, then we should
    classify two frayed ropes here (first we'd classify {0, 1, 2, 3, 4}, and
    later we'd classify {3-R, 4-R, 7, 8, 9}).

    However, since we now (circa Jan 2026) don't allow such cyclic frayed
    ropes, we will now classify neither structure as a frayed rope. (The
    rightmost structure can't be a frayed rope because 3 has that outgoing
    edge to 0.)

    NOTE: for some reason i forgot 5 and 6 when i was naming these nodes???
    so there are actually 8 nodes in this graph, despite what the node numbers
    might imply. lmao. i was so tired in 2020 or 2023 or something
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(2, 4)

    g.add_edge(3, 7)
    g.add_edge(4, 7)
    # this edge (now cyclic) just makes sure we don't identify this as a bubble
    g.add_edge(3, 0)

    g.add_edge(7, 8)
    g.add_edge(7, 9)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 8
        assert len(ag.decomposed_graph.edges) == 9
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 0
        # no splitting!
        assert len(ag.graph.nodes) == 8
        assert len(ag.graph.edges) == 9
    finally:
        os.close(fh)
        os.unlink(fn)


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
    ag = AssemblyGraph("metagenomescope/tests/input/chr21mat_subgraph_1.gv")
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


def test_chr21mat_minus653300458_splits_merged():
    r"""This is a pretty large graph, because for some reason trying to limit
    the graph to just the surrounding region of the impacted region prevents
    the problem from being reproduced -- probably some weird issue with the
    order in which nodes are traversed.

    Anyway this is similar to the test above -- node -653300458 is being split
    in a bug that used to impact MetagenomeScope, even though it shouldn't be.
    This verifies that the bug is fixed.

    For future reference, this problem was caused by trying to merge two chains
    (with an edge between them) into a parent chain both at once.
    """
    gv_fn = "metagenomescope/tests/input/chr21mat_subgraph_2.gv"
    ag = AssemblyGraph(gv_fn)
    _check_ag_topology_matches_gv(ag, gv_fn)


def test_chr15_pattern_resolution_fixed():
    """There's a weird bug with this graph where one of the nodes (686645112)
    has an outgoing edge to a "node" with the ID 99 that doesn't exist in the
    graph after decomposition is done.

    As of 2025, this was instead manifesting as node 262588926 remaining
    split despite it being unnecessary.

    Anyway, this test makes sure that both bugs do not impact this graph.
    Fixing https://github.com/marbl/MetagenomeScope/issues/267 appeared to
    resolve the problem.
    """
    gv_fn = "metagenomescope/tests/input/chr15_subgraph.gv"
    ag = AssemblyGraph(gv_fn)
    _check_ag_topology_matches_gv(ag, gv_fn)


def test_chr15_splitnode99bug_fixed():
    """Tests that the issue detailed in https://github.com/marbl/MetagenomeScope/issues/382
    is resolved. Swapping the order of the nodes in the chr15 graph swaps
    the order in which stuff happens in the decomposition, so this different
    version triggers this bug. WEIRD
    """
    gv_fn = "metagenomescope/tests/input/chr15_subgraph_noids.gv"
    ag = AssemblyGraph(gv_fn)
    _check_ag_topology_matches_gv(ag, gv_fn)


def test_chr15_full_chain_merging_bug_fixed():
    """Tests https://github.com/marbl/MetagenomeScope/issues/383 is fixed."""
    gv_fn = "metagenomescope/tests/input/chr15_full.gv"
    ag = AssemblyGraph(gv_fn)
    assert len(ag.components) == 1
    assert len(ag.nodename2objs["-200915910"]) == 1
    assert len(ag.nodename2objs["200915910"]) == 1
    n = ag.nodename2objs["-200915910"][0]
    in_edges = list(ag.graph.in_edges(n.unique_id))
    out_edges = list(ag.graph.out_edges(n.unique_id))
    assert len(in_edges) == 1
    assert len(out_edges) == 2
    in_id = in_edges[0][0]
    out_ids = [e[1] for e in out_edges]
    assert ag.nodeid2obj[in_id].name == "-105993978"
    out_names = [ag.nodeid2obj[i].name for i in out_ids]
    assert sorted(out_names) == ["-105993978", "43892573"]


def test_bubble_on_end_of_chain_etfe_trimming():
    r"""The input graph looks like

                 /--> 2 --\
    0 --> 5 --> 1          4
                 \--> 3 --/

    It should be decomposed into a chain containing a bubble:

                     +-----------------+
                     |     /--> 2 --\  |
    0 --> 5 --> 1-L ==> 1-R          4 |
                     |     \--> 3 --/  |
                     +-----------------+

    And then the node splitting should be undone, bringing us back to
    where we started but with the chain and bubble identified.

    See docs for is_edge_fake_and_trivial() for context.
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 5)
    g.add_edge(5, 1)
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 4)
    g.add_edge(3, 4)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 1
        assert len(ag.decomposed_graph.edges) == 0
        assert len(ag.chains) == 1
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 1
        assert len(ag.graph.nodes) == 6
        assert len(ag.graph.edges) == 6
    finally:
        os.close(fh)
        os.unlink(fn)


def test_isolated_bubble():
    r"""Is this actually explicitly tested anywhere else? I don't think so.

    The input graph looks like

     /--> 2 --\
    1          4
     \--> 3 --/

    It should be decomposed into just a single bubble, as you'd expect. No
    split nodes should be created (since 1 and 4 have no incoming / outgoing
    edges from outside the pattern, respectively) -- and even if they were
    to be created, no chains resulting from them should be created.

    See docs for is_edge_fake_and_trivial() for context.
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 4)
    g.add_edge(3, 4)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 1
        assert len(ag.decomposed_graph.edges) == 0
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 1
        assert len(ag.graph.nodes) == 4
        assert len(ag.graph.edges) == 4
    finally:
        os.close(fh)
        os.unlink(fn)


def test_cyclic_bulge():
    r"""The input graph looks like

     /-->\
    1 --> 2
     \<--/

    Should be labelled as a cyclic bulge, not a chain
    (https://github.com/marbl/MetagenomeScope/issues/251).
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(1, 2)
    g.add_edge(2, 1)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 1
        assert len(ag.decomposed_graph.edges) == 0
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 1
        assert len(ag.graph.nodes) == 2
        assert len(ag.graph.edges) == 3
    finally:
        os.close(fh)
        os.unlink(fn)


def test_split_start_node_with_incoming_edges_inside_pattern():
    r"""The input graph looks like

     /--> 2 --\ /----V
    1          4     5
     \--> 3 --/^----/

    This tests that node 4 is split, and that the incoming edge on
    node 4 (5 --> 4) points to 4-R (inside the cyclic chain) instead of 4-L.
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 4)
    g.add_edge(3, 4)
    g.add_edge(4, 5)
    g.add_edge(5, 4)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 1
        assert len(ag.decomposed_graph.edges) == 0
        assert len(ag.chains) == 1
        assert len(ag.cyclic_chains) == 1
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bubbles) == 1
        assert len(ag.graph.nodes) == 6
        assert len(ag.graph.edges) == 7

        five_to_four_r_edge_seen = False
        for src, tgt, d in ag.graph.edges(data=True):
            obj = ag.edgeid2obj[d["uid"]]
            sn = ag.nodeid2obj[src].name
            tn = ag.nodeid2obj[tgt].name
            if sn == "5" and tn == "4-R":
                five_to_four_r_edge_seen = True
                assert not obj.is_fake
                break
        assert five_to_four_r_edge_seen
    finally:
        os.close(fh)


def test_bipartite_series():
    r"""The input graph looks like

    1 -> 2 -> 5
      \/   \/
      /\   /\
    3 -> 4 -> 6

    This tests that we identify two bipartite patterns, one after the other.
    Nodes 2 and 4 should be split.
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(1, 4)
    g.add_edge(3, 2)
    g.add_edge(3, 4)
    g.add_edge(2, 5)
    g.add_edge(2, 6)
    g.add_edge(4, 5)
    g.add_edge(4, 6)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 2
        assert len(ag.decomposed_graph.edges) == 2
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bipartites) == 2
        assert len(ag.bubbles) == 0
        assert len(ag.graph.nodes) == 8
        assert len(ag.graph.edges) == 10
        assert sorted([n.name for n in ag.nodeid2obj.values()]) == [
            "1",
            "2-L",
            "2-R",
            "3",
            "4-L",
            "4-R",
            "5",
            "6",
        ]
    finally:
        os.close(fh)


def test_isolated_cyclic_bubble():
    r"""Tests that cyclic bubbles are no longer allowed. Regression test
    for https://github.com/marbl/MetagenomeScope/issues/241.

    Adapted from test_cyclic_bubbles_not_ok() in
    tests/graph/validators/test_bubble.py.

    +-------+
    |       |
    | /-1-\ |
    V/     \|
    0       3
     \     /
      \-2-/

    We should identify a chain from 3 -> 0 and LEAVE IT AT THAT LOLLLL
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 3)
    g.add_edge(0, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 0)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 3
        assert len(ag.decomposed_graph.edges) == 4
        assert len(ag.chains) == 1
        assert len(ag.cyclic_chains) == 0
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bipartites) == 0
        assert len(ag.bubbles) == 0
        assert len(ag.graph.nodes) == 4
        assert len(ag.graph.edges) == 5
        assert sorted([n.name for n in ag.nodeid2obj.values()]) == [
            "0",
            "1",
            "2",
            "3",
        ]
    finally:
        os.close(fh)


def test_isolated_cyclic_bubble_in_longer_chain():
    r"""Tests that bubbles in cyclic chains still work, so long
    as the cyclic chain contains stuff besides the bubble. Simpler
    version of test_chain_into_cyclic_chain_merging() -- tests that
    these kinds of graphs were not broken by the fix for
    https://github.com/marbl/MetagenomeScope/issues/241.

    +-------------+
    |             |
    | /-1-\       |
    V/     \      |
    0       3 --> 4
     \     /
      \-2-/
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 3)
    g.add_edge(0, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 4)
    g.add_edge(4, 0)

    fh, fn = nx2gml(g)
    try:
        ag = AssemblyGraph(fn)
        assert len(ag.decomposed_graph.nodes) == 1
        assert len(ag.decomposed_graph.edges) == 0
        assert len(ag.chains) == 0
        assert len(ag.cyclic_chains) == 1
        assert len(ag.frayed_ropes) == 0
        assert len(ag.bipartites) == 0
        assert len(ag.bubbles) == 1
        assert len(ag.graph.nodes) == 5
        assert len(ag.graph.edges) == 6
        assert sorted([n.name for n in ag.nodeid2obj.values()]) == [
            "0",
            "1",
            "2",
            "3",
            "4",
        ]
    finally:
        os.close(fh)
