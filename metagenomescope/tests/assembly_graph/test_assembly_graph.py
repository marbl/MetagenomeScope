from metagenomescope.graph_objects import AssemblyGraph
from metagenomescope.input_node_utils import negate_node_id
from metagenomescope import config
from pytest import approx


def test_scale_nodes():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # This graph has six nodes, with lengths 8, 10, 21, 7, 8, 4.
    #                          (for node IDs 1,  2,  3, 4, 5, 6.)
    ag.scale_nodes()
    nodename2rl = {
        "1": approx(0.4180047),
        "2": approx(0.5525722),
        "3": 1,
        "4": approx(0.3374782),
        "5": approx(0.4180047),
        "6": 0,
    }
    nodename2lp = {
        "1": config.MID_LONGSIDE_PROPORTION,
        "2": config.HIGH_LONGSIDE_PROPORTION,
        "3": config.HIGH_LONGSIDE_PROPORTION,
        "4": config.MID_LONGSIDE_PROPORTION,
        "5": config.MID_LONGSIDE_PROPORTION,
        "6": config.LOW_LONGSIDE_PROPORTION,
    }
    seen_nodenames = []
    for node in ag.digraph.nodes:
        name = ag.digraph.nodes[node]["name"]
        rl = ag.digraph.nodes[node]["relative_length"]
        lp = ag.digraph.nodes[node]["longside_proportion"]
        if name in nodename2rl:
            assert rl == nodename2rl[name]
            assert lp == nodename2lp[name]
        else:
            negated_name = negate_node_id(name)
            assert rl == nodename2rl[negated_name]
            assert lp == nodename2lp[negated_name]
        seen_nodenames.append(name)
    assert len(seen_nodenames) == 12


def test_scale_nodes_all_lengths_equal():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    # all of the nodes in this graph have length 3
    ag.scale_nodes()
    for node in ag.digraph.nodes:
        assert ag.digraph.nodes[node]["relative_length"] == 0.5
        assert (
            ag.digraph.nodes[node]["longside_proportion"]
            == config.MID_LONGSIDE_PROPORTION
        )


def test_has_edge_weights():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    assert not ag.has_edge_weights()

    ag = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
    assert ag.has_edge_weights()

    ag = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
    assert ag.has_edge_weights()


def test_get_edge_weight_field():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    assert ag.get_edge_weight_field() is None

    ag = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
    assert ag.get_edge_weight_field() is "multiplicity"

    ag = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
    assert ag.get_edge_weight_field() is "bsize"


def test_scale_edges_four_edges():
    # Really, there are two edges in this particular graph, but due to
    # reverse complementing we consider there to be four edges.
    ag = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
    ag.scale_edges()
    # No edges should have been flagged as outliers.
    # The two edges with weight 5 (the minimum weight in this dataset)
    # should've been assigned a relative weight of 0.
    # The two edges with weight 9 (the max weight) should've been assigned a
    # relative weight of 1.
    for edge in ag.digraph.edges:
        data = ag.digraph.edges[edge]
        assert not data["is_outlier"]
        if data["multiplicity"] == 5:
            assert data["relative_weight"] == 0
        else:
            assert data["relative_weight"] == 1


def test_scale_edges_no_edge_weights():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    ag.scale_edges()
    for edge in ag.digraph.edges:
        data = ag.digraph.edges[edge]
        assert not data["is_outlier"]
        assert data["relative_weight"] == 0.5
