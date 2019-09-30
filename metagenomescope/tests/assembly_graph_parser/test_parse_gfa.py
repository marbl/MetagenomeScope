# from .utils import run_tempfile_test
from metagenomescope.input_node_utils import negate_node_id
from metagenomescope.assembly_graph_parser import parse_gfa
from .utils import run_tempfile_test


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
        ("4", "4"),
    )
    for edge_id in expected_edges:
        assert edge_id in digraph.edges


def get_sample1_gfa():
    """Just returns a list representation of sample1.gfa, which as mentioned
    is from https://github.com/sjackman/gfalint/tree/master/examples.
    """
    # We could also just open and read the file, but this is easier to look at
    return [
        "H	VN:Z:1.0",
        "S	1	CGATGCAA",
        "S	2	TGCAAAGTAC",
        "S	3	TGCAACGTATAGACTTGTCAC	RC:i:4",
        "S	4	TATATGC",
        "S	5	CGATGATA",
        "S	6	ATGA",
        "L	1	+	2	+	5M",
        "L	3	+	2	+	0M",
        "L	3	+	4	-	1M1D3M",
        "L	4	-	5	+	0M"
    ]

def test_parse_no_length_node():
    s1 = get_sample1_gfa()
    s1.pop(1)
    s1.insert(1, "S\t1\t*")
    run_tempfile_test(
        "gfa", s1, ValueError, "Found a node without a specified length: 1"
    )

    # Manually assigning node 1 a sequence should fix the problem
    # (since the length is then implied)
    s1.pop(1)
    s1.insert(1, "S\t1\tAAA")
    run_tempfile_test("gfa", s1, None, None)

    # Similarly, explicitly giving node 1 a length should also be ok
    # (for reference, see
    # https://github.com/GFA-spec/GFA-spec/blob/master/GFA1.md#optional-fields-2)
    s1.pop(1)
    s1.insert(1, "S\t1\t*\tLN:i:6")
    run_tempfile_test("gfa", s1, None, None)
