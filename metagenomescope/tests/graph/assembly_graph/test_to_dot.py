import os
import re
import tempfile
import networkx as nx
from collections import defaultdict
from metagenomescope import config
from metagenomescope.graph import AssemblyGraph


def test_to_dot_bt1():
    r"""The input graph consists of a bubble inside a chain:

           2
          / \
    0 -> 1   4
          \ /
           3

    Verify that calling to_dot() on an AssemblyGraph created from this input
    graph produces a DOT file with the correct nodes, edges, and patterns
    included.
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test_1_in.gml")
    # just verify that the decomposition worked (this is already tested in
    # test_hierarchical_decomposition.py, but we might as well double-check
    # here)
    assert len(ag.decomposed_graph.nodes) == 1
    assert len(ag.decomposed_graph.edges) == 0
    assert len(ag.chains) == 1
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
    assert len(ag.graph.nodes) == 5
    assert len(ag.graph.edges) == 5

    try:
        fh, fn = tempfile.mkstemp(suffix=".gv")
        ag.to_dot(fn)

        # Load the output DOT file as a NX graph and check that the nodes and edges
        # look good
        dg = nx.nx_agraph.read_dot(fn)
        exp_area = config.MIN_NODE_AREA + (0.5 * config.NODE_AREA_RANGE)
        exp_width = exp_area**config.MID_LONGSIDE_PROPORTION
        exp_height = exp_area / exp_width
        seen_labels = []
        for n, data in dg.nodes(data=True):
            seen_labels.append(data["label"])
            assert data["shape"] == "invhouse"
            # NetworkX's read_dot() function seems to convert even numerical
            # data to strings. Not a big problem.
            assert data["width"] == str(exp_width)
            assert data["height"] == str(exp_height)
        assert sorted(seen_labels) == [
            "contig-100_0",
            "contig-100_1",
            "contig-100_2",
            "contig-100_3",
            "contig-100_4",
        ]
        seen_edges = []
        for (src, tgt, key) in dg.edges:
            # shouldn't be any parallel edges here
            assert key == 0
            seen_edges.append((dg.nodes[src]["label"], dg.nodes[tgt]["label"]))
        assert sorted(seen_edges) == [
            ("contig-100_0", "contig-100_1"),
            ("contig-100_1", "contig-100_2"),
            ("contig-100_1", "contig-100_3"),
            ("contig-100_2", "contig-100_4"),
            ("contig-100_3", "contig-100_4"),
        ]

        # verify that there are two clusters (patterns) defined in the file,
        # and that they contain the correct nodes (the chain should contain all
        # nodes, and the bubble should contain all nodes except for node 0).
        # this code is a bit gross but it works ;)

        # this is a regular expression that extracts the final character of a
        # node label, so we can figure out which nodes are in which clusters
        node_lbl_patt = re.compile(r"contig-100_(\d)")
        open_clusters = []
        cluster2nodes = defaultdict(list)
        with open(fn, "r") as fp:
            for line in fp:
                if "subgraph" in line:
                    # slice off the cluster name (e.g. "cluster_Chain_14")
                    open_clusters.append(line.split()[1])
                elif "}" in line:
                    if len(open_clusters) > 0:
                        open_clusters.pop()
                elif "shape" in line:
                    pm = node_lbl_patt.search(line)
                    assert pm is not None
                    node_lbl_num = pm.group(1)
                    for c in open_clusters:
                        cluster2nodes[c].append(node_lbl_num)
        assert sorted([cn.split("_")[1] for cn in cluster2nodes]) == [
            "Bubble",
            "Chain",
        ]
        bubble_name, chain_name = sorted(cluster2nodes)
        assert sorted(cluster2nodes[bubble_name]) == ["1", "2", "3", "4"]
        assert sorted(cluster2nodes[chain_name]) == ["0", "1", "2", "3", "4"]
    finally:
        os.close(fh)
        os.unlink(fn)
