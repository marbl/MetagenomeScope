import pytest
import networkx as nx
from metagenomescope import config
from metagenomescope.graph import validators
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
            config.PT_BUBBLE, True, [1, 2, 3], 1, None
        )
    assert "Start node = 1 but end node = None?" == str(ei.value)


def test_validation_results_repr():
    vr = validators.ValidationResults(config.PT_BUBBLE, True, [1, 2, 3], 1, 3)
    assert repr(vr) == (
        f"Valid pattern (type {config.PT_BUBBLE}) of nodes "
        "[1, 2, 3] from 1 to 3"
    )

    vr_fr = validators.ValidationResults(
        config.PT_FRAYEDROPE, True, [1, "a", 3]
    )
    assert repr(vr_fr) == (
        f"Valid pattern (type {config.PT_FRAYEDROPE}) of nodes [1, 'a', 3]"
    )

    vr_invalid = validators.ValidationResults()
    assert repr(vr_invalid) == "Not a valid pattern"

    # even if we specify a pattern type, it doesn't impact __repr__ if is_valid
    # is False
    vr_invalid2 = validators.ValidationResults(config.PT_BUBBLE)
    assert repr(vr_invalid2) == "Not a valid pattern"
