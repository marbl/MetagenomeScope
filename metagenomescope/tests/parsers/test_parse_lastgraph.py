import networkx as nx
from .utils import run_tempfile_test
from metagenomescope.errors import GraphParsingError
from metagenomescope.parsers import parse_lastgraph
from metagenomescope.tests.parsers.test_validate_lastgraph import reset_glines


def test_parse_lastgraph_good():
    digraph = parse_lastgraph(
        "metagenomescope/tests/input/cycletest_LastGraph"
    )
    # Verify that a NetworkX MultiDiGraph was computed based on this file
    # accurately.
    assert type(digraph) is nx.MultiDiGraph
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
    # (The 0s correspond to keys, since this is a multigraph)
    for edge_id in (("1", "2", 0), ("-2", "-1", 0)):
        assert edge_id in digraph.edges
        assert digraph.edges[edge_id]["multiplicity"] == 5
    for edge_id in (("2", "1", 0), ("-1", "-2", 0)):
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
        "LastGraph",
        glines,
        GraphParsingError,
        "Line 4: Node block ends too early.",
    )

    glines = reset_glines()
    glines[2] = "ARC\t1\t1\t5"
    run_tempfile_test(
        "LastGraph",
        glines,
        GraphParsingError,
        "Line 3: Node block ends too early.",
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


def test_parse_lastgraph_multigraph():
    glines = reset_glines()
    glines[8] = "ARC\t1\t2\t8"
    # This graph should now have four nodes (1, -1, 2, -2) and two edges
    # (1  -->  2 with multiplicity 5;
    #  -2 --> -1 with multiplicity 5;
    #  1  -->  2 with multiplicity 8;
    #  -2 --> -1 with multiplicity 8).
    g = run_tempfile_test("LastGraph", glines, None, None)
    assert len(g.nodes) == 4
    assert len(g.edges) == 4
    assert sorted(g.edges) == [
        ("-2", "-1", 0),
        ("-2", "-1", 1),
        ("1", "2", 0),
        ("1", "2", 1),
    ]
    # This order (of which edge has a key of 0 and which edge has a key of 1
    # according to NetworkX) should be consistent, since my LastGraph parser
    # goes line-by-line through the input file (so if there are two edges, the
    # first one listed in the file should have a key of 0 then the next one
    # should have a key of 1)
    assert g.edges[("1", "2", 0)]["multiplicity"] == 5
    assert g.edges[("-2", "-1", 0)]["multiplicity"] == 5
    assert g.edges[("1", "2", 1)]["multiplicity"] == 8
    assert g.edges[("-2", "-1", 1)]["multiplicity"] == 8


def test_parse_lastgraph_self_implying_edge():
    glines = reset_glines()
    glines[8] = "ARC\t2\t-2\t800"
    # +2 -> -2 has a complement of -(-2) -> -(+2) = +2 -> -2. So, it implies
    # itself. See https://github.com/marbl/MetagenomeScope/issues/240 for
    # details about how I hope to eventually handle this; for now, we just only
    # add this edge *once*.
    g = run_tempfile_test("LastGraph", glines, None, None)
    # There should be 4 nodes: 1, -1, 2, -2
    assert len(g.nodes) == 4
    # ... but only 3 edges: 1 -> 2, -2 -> -1, and 2 -> -2. This is because the
    # complement of 2 -> -2 is itself, as shown above.
    assert len(g.edges) == 3
    assert sorted(g.edges) == [
        ("-2", "-1", 0),
        ("1", "2", 0),
        ("2", "-2", 0),
    ]
    assert g.edges[("1", "2", 0)]["multiplicity"] == 5
    assert g.edges[("-2", "-1", 0)]["multiplicity"] == 5
    assert g.edges[("2", "-2", 0)]["multiplicity"] == 800
