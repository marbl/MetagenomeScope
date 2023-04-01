from metagenomescope.graph_objects import AssemblyGraph
from pytest import approx, raises


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
    assert ag.get_edge_weight_field() == "multiplicity"

    ag = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
    assert ag.get_edge_weight_field() == "bsize"


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
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        assert data["is_outlier"] == 0
        if data["multiplicity"] == 5:
            assert data["relative_weight"] == 0
        else:
            assert data["relative_weight"] == 1


def test_scale_edges_no_edge_weights():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    ag.scale_edges()
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        assert data["is_outlier"] == 0
        assert data["relative_weight"] == 0.5


def test_scale_edges_all_edge_weights_equal():
    ag = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
    ag.scale_edges()
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        assert data["is_outlier"] == 0
        assert data["relative_weight"] == 0.5


def test_scale_edges_less_than_4_edges():
    ag = AssemblyGraph("metagenomescope/tests/input/1_node_1_edge.LastGraph")
    ag.scale_edges()
    # I mean, I guess it really has 2 edges if we assume it's unoriented
    # (which as of writing is the default for LastGraph / GFAs but not
    # required)
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        # No outlier detection should be done
        assert data["is_outlier"] == 0
        # Normal, relative scaling should have been done -- in this particular
        # case both edges have the same weight so they both get 0.5 for their
        # relative weight
        assert data["relative_weight"] == 0.5


def test_scale_edges_high_outlier():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_high.LastGraph"
    )
    ag.scale_edges()
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        # We omit the outlier edge weight (1000) from the non-outlier-edge
        # relative scaling. So the "effective" min and max edge weights are 5
        # and 99, ignoring the 1000s.
        if data["multiplicity"] == 5:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 0
        elif data["multiplicity"] == 9:
            assert data["is_outlier"] == 0
            # (9 - 5) / (99 - 5) = 4 / 94 = 0.04255319...
            assert data["relative_weight"] == approx(0.0425532)
        elif data["multiplicity"] == 99:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 1
        else:
            # The edges with weight 1000 are high outliers!
            assert data["is_outlier"] == 1
            assert data["relative_weight"] == 1


def test_scale_edges_low_outlier():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_low.LastGraph"
    )
    ag.scale_edges()
    # Low outlier weights: 1
    # Non-outlier weights: 1000, 1001, 1005
    for edge in ag.graph.edges:
        data = ag.graph.edges[edge]
        if data["multiplicity"] == 1:
            assert data["is_outlier"] == -1
            assert data["relative_weight"] == 0
        elif data["multiplicity"] == 1000:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 0
        elif data["multiplicity"] == 1001:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 1 / 5
        else:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 1


def _verify_both_graph(digraph, expected_dups=0):
    """Verifies the edge scaling values for all of the (real) edges in the
    edge_scaling_test_both_outliers.LastGraph test graph.

    Made this into a function so it can be reused between tests.
    """
    # Low outlier weights: 1
    # High outlier weights: 2001
    # Non-outlier weights: 1000, 1001, 1005
    for edge in digraph.edges:
        data = digraph.edges[edge]
        if data["multiplicity"] == 1:
            assert data["is_outlier"] == -1
            assert data["relative_weight"] == 0
        elif data["multiplicity"] == 1000:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 0
        elif data["multiplicity"] == 1001:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 1 / 5
        elif data["multiplicity"] == 1005:
            assert data["is_outlier"] == 0
            assert data["relative_weight"] == 1
        else:
            assert data["is_outlier"] == 1
            assert data["relative_weight"] == 1


def test_scale_edges_low_and_high_outliers():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_both_outliers.LastGraph"
    )
    ag.scale_edges()
    _verify_both_graph(ag.graph, 0)


def test_scale_edges_dup_edges():
    """Test that edges marked with is_dup = True cause an error.

    These particular edges are only used (as of writing, at least) to connect a
    node with its duplicate. Scaling them doesn't make sense, since they don't
    have any weight or anything (since they're not "real" edges). They
    shouldn't even exist in the graph, yet! So if they exist, we raise an
    error.
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/edge_scaling_test_both_outliers.LastGraph"
    )
    ag.graph.add_edge(0, 0, is_dup=True)
    with raises(ValueError) as ei:
        ag.scale_edges()
    assert str(ei.value) == "Duplicate edges shouldn't exist in the graph yet."
