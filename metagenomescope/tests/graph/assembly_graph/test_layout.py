import pytest
from metagenomescope.graph import AssemblyGraph


def test_ccs_avoided_due_to_max_node_ct(capsys):
    AssemblyGraph("metagenomescope/tests/input/sample1.gfa", max_node_count=2)
    # For now, just check the print messages.
    # https://docs.pytest.org/en/stable/capture.html
    captured = capsys.readouterr()
    # (the first message about not laying out a cmp with 5 nodes and 4 edges
    # occurs twice)
    exp_msgs = (
        "Ignoring a component (5 nodes, 4 edges): exceeds -maxn or -maxe.",
        "Laying out small (each containing < 5 nodes) remaining component(s)...",
    )
    for m in exp_msgs:
        assert m in captured.out


def test_error_if_all_ccs_avoided():
    with pytest.raises(ValueError) as ei:
        AssemblyGraph(
            "metagenomescope/tests/input/sample1.gfa", max_node_count=0
        )
    assert "All components were too large to lay out." in str(ei.value)
