from metagenomescope.graph import AssemblyGraph


def test_simple_pattern_layout():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")
    ag.scale_nodes()
    ag.compute_node_dimensions()
    ag.scale_edges()
    ag.hierarchically_identify_patterns()

    # This graph should contain just a single bubble. We're going to verify
    # that laying it out works as expected.
    assert len(ag.bubbles) == 1
    p = ag.bubbles[0]
    p.layout(ag)

    # Verify that the layout looks reasonable
    # w, h = p.width, p.height
    # TODO: assert stuff about the layout


# TODO: test more complex cases, e.g. with duplicate nodes/edges and with
# nested patterns
