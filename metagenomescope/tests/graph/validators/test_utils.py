import pytest
import networkx as nx
from metagenomescope import config
from metagenomescope.graph import validators, Node, Edge
from metagenomescope.errors import WeirdError


def test_verify_node_in_graph():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    validators.verify_node_in_graph(g, 0)
    validators.verify_node_in_graph(g, 1)
    with pytest.raises(WeirdError) as ei:
        validators.verify_node_in_graph(g, 2)
    assert "Node 2 is not present in the graph's nodes?" in str(ei.value)


def test_validation_results_bad_start_end():
    with pytest.raises(WeirdError) as ei:
        validators.ValidationResults(
            config.PT_BUBBLE, True, [1, 2, 3], [1], [4]
        )
    assert str(ei.value) == "[4] is not a subset of [1, 2, 3]"


def test_validation_results_bad_pattern_type():
    with pytest.raises(WeirdError) as ei:
        validators.ValidationResults("bubble???", True, [1, 2, 3], [1], [3])
    assert str(ei.value) == "Invalid pattern type: bubble???"


def test_validation_results_repr():
    vr = validators.ValidationResults(
        config.PT_BUBBLE, True, [1, 2, 3], [1], [3]
    )
    assert repr(vr) == "Valid Bubble of nodes [1, 2, 3] from [1] to [3]"

    vr_fr = validators.ValidationResults(
        config.PT_FRAYEDROPE, True, [1, "a", 2, 3, 4], [1, "a"], [3]
    )
    assert repr(vr_fr) == (
        "Valid Frayed Rope of nodes [1, 'a', 2, 3, 4] from [1, 'a'] to [3]"
    )

    vr_invalid = validators.ValidationResults()
    assert repr(vr_invalid) == "Invalid pattern"

    # even if we specify a pattern type, it doesn't impact __repr__ if is_valid
    # is False
    vr_invalid2 = validators.ValidationResults(config.PT_BUBBLE)
    assert repr(vr_invalid2) == "Invalid pattern"


def test_fail_if_not_single_edge():
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(1, 2)

    # bad case -- parallel outgoing edges
    with pytest.raises(WeirdError) as ei:
        validators.fail_if_not_single_edge(g, g.adj[0], "sus", "outgoing")
    assert str(ei.value) == "Node ID sus doesn't have exactly 1 outgoing edge?"

    # bad case -- 0 incoming edges
    with pytest.raises(WeirdError) as ei:
        validators.fail_if_not_single_edge(g, g.pred[0], "sus", "incoming")
    assert str(ei.value) == "Node ID sus doesn't have exactly 1 incoming edge?"

    # good cases
    validators.fail_if_not_single_edge(g, g.adj[1], "sus1", "outgoing")
    validators.fail_if_not_single_edge(g, g.pred[2], "sus2", "incoming")


def test_is_edge_fake_and_trivial_bad():
    # Test the case where there exists a fake edge between two non-pattern
    # nodes. Since this should never happen in practice, the function should
    # throw an error.
    g = nx.MultiDiGraph()
    g.add_edge(0, 1, uid=2)
    nodeid2obj = {0: Node(0, "0", {}), 1: Node(1, "1", {})}
    edgeid2obj = {2: Edge(2, 0, 1, {}, is_fake=True)}
    with pytest.raises(WeirdError) as ei:
        validators.is_edge_fake_and_trivial(g, 0, 1, nodeid2obj, edgeid2obj)
    assert str(ei.value) == "Non-pattern nodes (0, 1) connected by fake edge?"
