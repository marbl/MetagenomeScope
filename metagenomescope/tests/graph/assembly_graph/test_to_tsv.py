import os
import tempfile
import pandas as pd
from metagenomescope.graph import AssemblyGraph


def test_to_tsv_bt1():
    r"""The input graph consists of a bubble inside a chain:

           2
          / \
    0 -> 1   4
          \ /
           3

    This is a simple test; after decomposition is finished, the graph has no
    remaining split nodes or fake edges.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test_1_in.gml")
    # double-check that the decomposition worked
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bipartites) == 0
    assert len(ag.bubbles) == 1
    assert len(ag.graph.nodes) == 5
    assert len(ag.graph.edges) == 5

    try:
        fh, fn = tempfile.mkstemp(suffix=".tsv")
        ag.to_tsv(fn)
        df = pd.read_csv(fn, sep="\t", index_col=0)
        pd.testing.assert_frame_equal(
            df,
            pd.DataFrame(
                {
                    "Nodes": [5],
                    "Edges": [5],
                    "Bubbles": [1],
                    "Chains": [1],
                    "CyclicChains": [0],
                    "FrayedRopes": [0],
                    "Bipartites": [0],
                },
                index=pd.Index([1], name="Component"),
            ),
        )
    finally:
        os.close(fh)
        os.unlink(fn)


def test_to_tsv_bubble_cyclic_chain():
    r"""The input graph consists of bubbles in a cyclic chain. Decomposes into:

    +=======================================+
    |                                       |
    | +-------+-------+--------+---------+  |
    | |   2   |   5   |   8    |    11   |  |
    | |  / \  |  / \  |  / \   |   /  \  |  |
    +== 1   4 = 4   7 = 7   10 = 10    1 ===+
      |  \ /  |  \ /  |  \ /   |   \  /  |
      |   3   |   6   |   9    |    12   |
      +-------+-------+--------+---------+

    The decomposition has fake nodes and edges, so this checks how to_tsv()
    handles those. (As of Jan 2026, it should ignore them -- it should be as
    if the graph remained unmodified.)
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )
    # double-check that the decomposition worked
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 0
    assert len(ag.cyclic_chains) == 1
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bipartites) == 0
    assert len(ag.bubbles) == 4
    assert len(ag.graph.nodes) == 16
    assert len(ag.graph.edges) == 20

    try:
        fh, fn = tempfile.mkstemp(suffix=".tsv")
        ag.to_tsv(fn)
        df = pd.read_csv(fn, sep="\t", index_col=0)
        pd.testing.assert_frame_equal(
            df,
            pd.DataFrame(
                {
                    "Nodes": [12],
                    "Edges": [16],
                    "Bubbles": [4],
                    "Chains": [0],
                    "CyclicChains": [1],
                    "FrayedRopes": [0],
                    "Bipartites": [0],
                },
                index=pd.Index([1], name="Component"),
            ),
        )
    finally:
        os.close(fh)
        os.unlink(fn)


def check_sample1gfa_tsv(fn):
    df = pd.read_csv(fn, sep="\t", index_col=0)
    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            {
                "Nodes": [5, 5, 1, 1],
                "Edges": [4, 4, 0, 0],
                "Bubbles": [0, 0, 0, 0],
                "Chains": [1, 1, 0, 0],
                "CyclicChains": [0, 0, 0, 0],
                "FrayedRopes": [0, 0, 0, 0],
                "Bipartites": [0, 0, 0, 0],
            },
            index=pd.Index([1, 2, 3, 4], name="Component"),
        ),
    )


def test_to_tsv_bubble_sample1gfa():
    """sample1.gfa has multiple components, which is why we use it here."""
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    try:
        fh, fn = tempfile.mkstemp(suffix=".tsv")
        ag.to_tsv(fn)
        check_sample1gfa_tsv(fn)
    finally:
        os.close(fh)
        os.unlink(fn)
