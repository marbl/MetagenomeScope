from metagenomescope.graph import AssemblyGraph


def test_to_treemap():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.to_treemap() == (
        ["Components", "#1", "#2", "#3", "#4"],
        ["", "Components", "Components", "Components", "Components"],
        [12, 5, 5, 1, 1],
    )
