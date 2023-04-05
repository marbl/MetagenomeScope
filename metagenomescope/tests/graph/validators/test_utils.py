import pytest
import networkx as nx
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
        validators.ValidationResults(True, [1, 2, 3], 1, None)
    assert "Starting node = 1 but ending node = None?" == str(ei.value)


def test_validation_results_repr():
    vr = validators.ValidationResults(True, [1, 2, 3], 1, 3)
    assert repr(vr) == "Valid pattern of nodes [1, 2, 3] from 1 to 3"

    vr_fr = validators.ValidationResults(True, [1, "a", 3])
    assert repr(vr_fr) == "Valid pattern of nodes [1, 'a', 3]"

    vr_invalid = validators.ValidationResults()
    assert repr(vr_invalid) == "Not a valid pattern"
