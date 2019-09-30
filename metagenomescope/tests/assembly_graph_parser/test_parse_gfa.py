# from .utils import run_tempfile_test
from metagenomescope.input_node_utils import negate_node_id
from metagenomescope.assembly_graph_parser import parse_gfa


def check_sample_gfa_digraph(digraph):
    """Checks that all of the collected data (nodes, edges, node gc content)
    looks good for the NX DiGraph produced by running parse_gfa() on
    sample1.gfa or sample2.gfa.

    (sample1.gfa and sample2.gfa describe the same graph structure, albeit in
    GFA1 and GFA2 respectively.)

    Using the same assertions on the output of parsing both graphs has two
    benefits: 1) it lets us ensure that these graphs are equal (at least in
    the ways parse_gfa() cares about), and 2) it lets me be lazy and reuse all
    of this test code ;)
    """
    assert len(digraph.nodes) == 12
    assert len(digraph.edges) == 8

    for node_id in ("1", "2", "3", "4", "5", "6"):
        assert node_id in digraph.nodes
        assert negate_node_id(node_id) in digraph.nodes

    for node_id in ("1", "-1"):
        assert digraph.nodes[node_id]["length"] == 8
        assert digraph.nodes[node_id]["gc_content"] == 0.5

    for node_id in ("2", "-2"):
        assert digraph.nodes[node_id]["length"] == 10
        assert digraph.nodes[node_id]["gc_content"] == 0.4

    for node_id in ("3", "-3"):
        assert digraph.nodes[node_id]["length"] == 21
        assert digraph.nodes[node_id]["gc_content"] == (9 / 21)

    for node_id in ("4", "-4"):
        assert digraph.nodes[node_id]["length"] == 7
        assert digraph.nodes[node_id]["gc_content"] == (2 / 7)

    for node_id in ("5", "-5"):
        assert digraph.nodes[node_id]["length"] == 8
        assert digraph.nodes[node_id]["gc_content"] == (3 / 8)

    for node_id in ("6", "-6"):
        assert digraph.nodes[node_id]["length"] == 4
        assert digraph.nodes[node_id]["gc_content"] == 0.25

    expected_edges = (
        ("1", "2"),
        ("-2", "-1"),
        ("3", "2"),
        ("-2", "-3"),
        ("3", "-4"),
        ("4", "-3"),
        ("-4", "5"),
        ("-5", "4"),
    )
    for edge_id in expected_edges:
        assert edge_id in digraph.edges


def test_parse_gfa1_good():
    check_sample_gfa_digraph(
        parse_gfa("metagenomescope/tests/input/sample1.gfa")
    )


def test_parse_gfa2_good():
    check_sample_gfa_digraph(
        parse_gfa("metagenomescope/tests/input/sample2.gfa")
    )

def test_parse_self_implied_edge():
    """Uses loop.gfa (c/o Shaun Jackman) to test self-implied GFA edges.

    We define a "self-implied edge" as an edge whose complement is itself. An
    example of such an edge is 2+ -> 2- in loop.gfa; the complement of this
    edge is -(2-) -> -(2+), which is equal to 2+ -> 2- (my notation looks kind
    of sillyt but you get the idea).

    The expected behavior is that self-implied edges are only added to the
    assembly graph visualization once, since duplicate edges in general don't
    really make sense here. This corroborates the visualization of loop.gfa in
    Shaun's repository containing it
    (https://github.com/sjackman/assembly-graph).
    """
    digraph = parse_gfa("metagenomescope/tests/input/loop.gfa")
    assert len(digraph.nodes) == 8

    # Even though there are 4 edges specified in loop.gfa, we only expect *6*
    # edges to be in the output graph: 2+ -> 2- and 3- -> 3+ are both
    # self-implying, so we don't add their "complements."
    assert len(digraph.edges) == 6

    expected_edges = (
        ("1", "1"),
        ("-1", "-1"),
        ("2", "-2"),
        ("-3", "3"),
        ("-4", "-4"),
        ("4", "4")
    )
    for edge_id in expected_edges:
        assert edge_id in digraph.edges
