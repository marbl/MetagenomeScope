from metagenomescope.graph import AssemblyGraph


def test_simple_pattern_layout():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")

    # This graph should contain just a single bubble. We're going to verify
    # that laying it out works as expected.
    # NOTE: Refactoring things so that initializing an AssemblyGraph
    # automatically runs layout, etc mighta broken this test. might need to
    # just update test to look at the layout directly without calling
    # p.layout()
    assert len(ag.bubbles) == 1
    p = ag.bubbles[0]
    p.layout(ag)

    # Verify that the layout looks reasonable
    # w, h = p.width, p.height
    # TODO: assert stuff about the layout


# TODO: test more complex cases, e.g. with duplicate nodes/edges and with
# nested patterns
