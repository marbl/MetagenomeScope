from metagenomescope.graph import AssemblyGraph


def test_to_treemap_no_aggregation():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.to_treemap() == (
        ["Components", "#1", "#2", "#3", "#4"],
        ["", "Components", "Components", "Components", "Components"],
        [12, 5, 5, 1, 1],
    )


def test_to_treemap_aggregation():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.to_treemap(min_large_cc_ct=4) == (
        [
            "Components",
            "#1 \u2013 2 (5-node components)",
            "#3 \u2013 4 (1-node components)",
        ],
        ["", "Components", "Components"],
        [12, 10, 2],
    )
