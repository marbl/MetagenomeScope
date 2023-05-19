import pytest
from metagenomescope.graph import AssemblyGraph


def test_ccs_avoided_due_to_max_node_ct(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa", max_node_count=2
    )
    # For now, just check the print messages.
    # https://docs.pytest.org/en/stable/capture.html
    captured = capsys.readouterr()
    msgs = (
        "Removing components with > 2 nodes and/or > 7,999 edges...",
        "Ignoring a component with 5 nodes and 4 edges.",
    )
    for em in msgs:
        assert em in captured.out
    # there should just be two ccs left, each containing a single node
    assert sorted([n.name for n in ag.nodeid2obj.values()]) == ["-6", "6"]
    assert len(ag.get_connected_components()) == 2


def test_error_if_all_ccs_avoided():
    with pytest.raises(ValueError) as ei:
        AssemblyGraph(
            "metagenomescope/tests/input/bubble_chain_test.gml",
            max_node_count=3,
        )
    assert "All components were too large to lay out." in str(ei.value)


def test_no_max_node_or_edge_count(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa",
        max_node_count=0,
        max_edge_count=0,
    )
    captured = capsys.readouterr()
    assert "Removing components with" not in captured.out
    assert "Ignoring a component" not in captured.out
    assert len(ag.nodeid2obj) == 12
    assert len(ag.get_connected_components()) == 4


def test_no_max_edge_count(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa",
        max_node_count=4,
        max_edge_count=0,
    )
    captured = capsys.readouterr()
    msgs = (
        "Removing components with > 4 nodes...",
        "Ignoring a component with 5 nodes and 4 edges.",
    )
    for em in msgs:
        assert em in captured.out
    assert len(ag.nodeid2obj) == 2
    assert len(ag.get_connected_components()) == 2


def test_no_max_node_count(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa",
        max_node_count=0,
        max_edge_count=3,
    )
    captured = capsys.readouterr()
    msgs = (
        "Removing components with > 3 edges...",
        "Ignoring a component with 5 nodes and 4 edges.",
    )
    for em in msgs:
        assert em in captured.out
    assert len(ag.nodeid2obj) == 2
    assert len(ag.get_connected_components()) == 2


def test_exactly_equal_to_max_node_ct(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa",
        max_node_count=5,
        max_edge_count=1234,
    )
    captured = capsys.readouterr()
    assert (
        "Removing components with > 5 nodes and/or > 1,234 edges..."
        in captured.out
    )
    assert "Ignoring a component" not in captured.out
    assert len(ag.nodeid2obj) == 12
    assert len(ag.get_connected_components()) == 4


def test_exactly_equal_to_max_edge_ct(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa",
        max_node_count=10,
        max_edge_count=4,
    )
    captured = capsys.readouterr()
    assert (
        "Removing components with > 10 nodes and/or > 4 edges..."
        in captured.out
    )
    assert "Ignoring a component" not in captured.out
    assert len(ag.nodeid2obj) == 12
    assert len(ag.get_connected_components()) == 4
