import pytest
from metagenomescope.errors import WeirdError
from metagenomescope.graph import AssemblyGraph


def test_to_treemap_one_cc_fails():
    # this graph is just a single bubble
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")
    with pytest.raises(WeirdError) as ei:
        ag.to_treemap()
    assert str(ei.value) == "Graph has only a single component"


def test_to_treemap_no_aggregation():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.to_treemap(min_large_cc_ct=100) == (
        ["Components", "#1", "#2", "#3", "#4"],
        ["", "Components", "Components", "Components", "Components"],
        [12, 5, 5, 1, 1],
        [False, False, False, False, False],
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
        [False, True, True],
    )
