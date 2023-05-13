from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import WeirdError
from pytest import approx, raises


def test_get_edge_weight_field():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    assert ag.get_edge_weight_field() is None

    ag = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
    assert ag.get_edge_weight_field() == "multiplicity"

    ag = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
    assert ag.get_edge_weight_field() == "bsize"


def test_scale_edges_four_edges():
    # Really, there are two edges in this particular graph, but due to
    # reverse complementing we consider there to be four edges.
    ag = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
    # No edges should have been flagged as outliers.
    # The two edges with weight 5 (the minimum weight in this dataset)
    # should've been assigned a relative weight of 0.
    # The two edges with weight 9 (the max weight) should've been assigned a
    # relative weight of 1.
    for edge in ag.edgeid2obj.values():
        assert edge.is_outlier == 0
        if edge.data["multiplicity"] == 5:
            assert edge.relative_weight == 0
        else:
            assert edge.relative_weight == 1


def _verify_no_outliers_and_rw_pt5(graph_fp):
    ag = AssemblyGraph(graph_fp)
    for edge in ag.edgeid2obj.values():
        assert edge.is_outlier == 0
        assert edge.relative_weight == 0.5


def test_scale_edges_no_edge_weights():
    _verify_no_outliers_and_rw_pt5("metagenomescope/tests/input/loop.gfa")


def test_scale_edges_all_edge_weights_equal():
    _verify_no_outliers_and_rw_pt5(
        "metagenomescope/tests/input/marygold_fig2a.gml"
    )


def test_scale_edges_less_than_4_edges():
    # I mean, I guess it really has 2 edges if we assume it's unoriented
    # (which as of writing is the default for LastGraph / GFAs but not
    # required)
    # No outlier detection should be done;
    # Normal, relative scaling should have been done -- in this particular
    # case both edges have the same weight so they both get 0.5 for their
    # relative weight
    _verify_no_outliers_and_rw_pt5(
        "metagenomescope/tests/input/1_node_1_edge.LastGraph"
    )


def _raise_mult_error(mult):
    raise AssertionError(
        f"Why's an edge in this test graph have multiplicity {mult}?"
    )


def test_scale_edges_high_outlier():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_high.LastGraph"
    )
    for edge in ag.edgeid2obj.values():
        mult = edge.data["multiplicity"]
        # We omit the outlier edge weight (1000) from the non-outlier-edge
        # relative scaling. So the "effective" min and max edge weights are 5
        # and 99, ignoring the 1000s.
        if mult == 5:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 0
        elif mult == 9:
            assert edge.is_outlier == 0
            # (9 - 5) / (99 - 5) = 4 / 94 = 0.04255319...
            assert edge.relative_weight == approx(0.0425532)
        elif mult == 99:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 1
        elif mult == 1000:
            # The edges with weight 1000 are high outliers!
            assert edge.is_outlier == 1
            assert edge.relative_weight == 1
        else:
            _raise_mult_error(mult)


def test_scale_edges_low_outlier():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_low.LastGraph"
    )
    # Low outlier weights: 1
    # Non-outlier weights: 1000, 1001, 1005
    for edge in ag.edgeid2obj.values():
        mult = edge.data["multiplicity"]
        if mult == 1:
            assert edge.is_outlier == -1
            assert edge.relative_weight == 0
        elif mult == 1000:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 0
        elif mult == 1001:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 1 / 5
        elif mult == 1005:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 1
        else:
            _raise_mult_error(mult)


def test_scale_edges_low_and_high_outliers():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_both_outliers.LastGraph"
    )
    # Low outlier weights: 1
    # High outlier weights: 2001
    # Non-outlier weights: 1000, 1001, 1005
    for edge in ag.edgeid2obj.values():
        mult = edge.data["multiplicity"]
        if mult == 1:
            assert edge.is_outlier == -1
            assert edge.relative_weight == 0
        elif mult == 1000:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 0
        elif mult == 1001:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 1 / 5
        elif mult == 1005:
            assert edge.is_outlier == 0
            assert edge.relative_weight == 1
        elif mult == 2001:
            assert edge.is_outlier == 1
            assert edge.relative_weight == 1
        else:
            _raise_mult_error(mult)


def test_scale_edges_fakes_not_expected():
    """Test that edges marked as fake cause an error.

    These particular edges are only used (as of writing, at least) to connect a
    node that has been split with its counterpart node. Scaling these edges
    doesn't make sense, since they don't have any weight or anything (they're
    not "real" edges). They shouldn't even exist in the graph, yet! So if they
    exist, we raise an error.

    It's kinda hard to test this because AssemblyGraph._scale_edges() is called
    from the AssemblyGraph constructor (__init__()) -- we cheat by calling
    _scale_edges() for a second time here after creating a graph. This should
    trigger an error if the graph in question contains any fake edges (which is
    the case for the bubble chain test graph).
    """
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_test.gml")
    with raises(WeirdError) as ei:
        ag._scale_edges()
    assert str(ei.value) == "Fake edges shouldn't exist in the graph yet."
