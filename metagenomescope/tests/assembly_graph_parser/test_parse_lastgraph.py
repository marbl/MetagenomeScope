from .utils import run_tempfile_test
from metagenomescope.errors import GraphParsingError
from metagenomescope.assembly_graph_parser import parse_lastgraph
from metagenomescope.tests.assembly_graph_parser.test_validate_lastgraph import (
    reset_glines,
)


def test_parse_lastgraph_good():
    digraph = parse_lastgraph(
        "metagenomescope/tests/input/cycletest_LastGraph"
    )
    # Verify that a NetworkX DiGraph was computed based on this file accurately
    # We expect 4 nodes and 4 edges due to the graph being interpreted as
    # unoriented (i.e. each node's forward or reverse orientation can be used)
    assert len(digraph.nodes) == 4
    assert len(digraph.edges) == 4

    # Check various node attributes individually
    # NOTE that a part of why we check these individually is because, in
    # LastGraph files, the forward and reverse sequences are not perfect
    # reverse complements of each other (they differ by an offset; see
    # https://github.com/rrwick/Bandage/wiki/Assembler-differences for a great
    # explanation of this). So it's acceptable for the GC content of node "ABC"
    # and node "-ABC" to be different.
    assert "1" in digraph.nodes
    assert digraph.nodes["1"]["length"] == 1
    assert digraph.nodes["1"]["depth"] == 5
    assert digraph.nodes["1"]["gc_content"] == 1

    assert "-1" in digraph.nodes
    assert digraph.nodes["-1"]["length"] == 1
    assert digraph.nodes["-1"]["depth"] == 5
    assert digraph.nodes["-1"]["gc_content"] == 0

    assert "2" in digraph.nodes
    assert digraph.nodes["2"]["length"] == 6
    assert digraph.nodes["2"]["depth"] == (20 / 6)
    assert digraph.nodes["2"]["gc_content"] == (2 / 3)

    assert "-2" in digraph.nodes
    assert digraph.nodes["-2"]["length"] == 6
    assert digraph.nodes["-2"]["depth"] == (20 / 6)
    assert digraph.nodes["-2"]["gc_content"] == (1 / 6)

    # Check that edges were properly stored in the digraph
    for edge_id in (("1", "2"), ("-2", "-1")):
        assert edge_id in digraph.edges
        assert digraph.edges[edge_id]["multiplicity"] == 5
    for edge_id in (("2", "1"), ("-1", "-2")):
        assert edge_id in digraph.edges
        assert digraph.edges[edge_id]["multiplicity"] == 9


# The remaining functions in this file test a few expected-to-fail LastGraph
# files. These should all be caught by validate_lastgraph_file(), which we've
# already thoroughly unit-tested using these same exact inputs, so this isn't
# very comprehensive -- essentially, these just check that yes, we are calling
# validate_lastgraph_file() from parse_lastgraph().
# A potential TODO here is porting over all of the validate_lastgraph_file()
# tests here, but I'm not sure that's really necessary.


def test_parse_lastgraph_node_interrupted():
    glines = reset_glines()
    glines.pop(3)
    run_tempfile_test(
        "LastGraph", glines, GraphParsingError, "Line 4: Node block ends too early."
    )

    glines = reset_glines()
    glines[2] = "ARC\t1\t1\t5"
    run_tempfile_test(
        "LastGraph", glines, GraphParsingError, "Line 3: Node block ends too early."
    )


def test_parse_lastgraph_invalid_node_count():
    glines = reset_glines()
    exp_msg = "Line 1: $NUMBER_OF_NODES must be a positive integer"

    glines[0] = "3.5\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "-3.5\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "-2\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "2.0\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "ABC\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "0x123\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)

    glines[0] = "0\t10\t1\t1"
    run_tempfile_test("LastGraph", glines, GraphParsingError, exp_msg)
