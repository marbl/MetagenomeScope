from metagenomescope.graph_objects import AssemblyGraph


def test_ccs_avoided_due_to_max_node_ct(capsys):
    ag = AssemblyGraph(
        "metagenomescope/tests/input/sample1.gfa", max_node_count=2
    )
    ag.scale_nodes()
    ag.compute_node_dimensions()
    ag.scale_edges()
    ag.hierarchically_identify_patterns()

    ag.layout()
    # For now, just check the print messages.
    # https://docs.pytest.org/en/stable/capture.html
    captured = capsys.readouterr()
    exp_msgs = (
        (
            "Not laying out component 1 (5 nodes, 4 edges): exceeds -maxn or "
            "-maxe."
        ),
        (
            "Not laying out component 2 (5 nodes, 4 edges): exceeds -maxn or "
            "-maxe."
        ),
        (
            "Laying out small (each containing < 5 nodes) remaining "
            "component(s)..."
        ),
    )
    for m in exp_msgs:
        assert m in captured.out
