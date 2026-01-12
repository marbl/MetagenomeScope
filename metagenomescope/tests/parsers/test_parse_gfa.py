import networkx as nx
from metagenomescope import config
from metagenomescope.name_utils import negate
from metagenomescope.parsers import parse_gfa
from metagenomescope.errors import GraphParsingError
from .utils import run_tempfile_test
from gfapy.error import InconsistencyError, NotUniqueError


def check_sample_gfa_digraph(digraph):
    """Checks that all of the collected data (nodes, edges, node gc content)
    looks good for the NX MultiDiGraph produced by running parse_gfa() on
    sample1.gfa or sample2.gfa.

    (sample1.gfa and sample2.gfa describe the same graph structure, albeit in
    GFA1 and GFA2 respectively.)

    Using the same assertions on the output of parsing both graphs has two
    benefits: 1) it lets us ensure that these graphs are equal (at least in
    the ways parse_gfa() cares about), and 2) it lets me be lazy and reuse all
    of this test code ;)
    """
    assert type(digraph) is nx.MultiDiGraph
    assert len(digraph.nodes) == 12
    assert len(digraph.edges) == 8

    for node_id in ("1", "2", "3", "4", "5", "6"):
        assert node_id in digraph.nodes
        assert negate(node_id) in digraph.nodes

    for node_id in ("1", "-1"):
        assert digraph.nodes[node_id]["length"] == 8
        assert digraph.nodes[node_id]["gc_content"] == 0.5
        assert digraph.nodes[node_id]["cov"] is None

    for node_id in ("2", "-2"):
        assert digraph.nodes[node_id]["length"] == 10
        assert digraph.nodes[node_id]["gc_content"] == 0.4
        assert digraph.nodes[node_id]["cov"] is None

    for node_id in ("3", "-3"):
        assert digraph.nodes[node_id]["length"] == 21
        assert digraph.nodes[node_id]["gc_content"] == (9 / 21)
        assert digraph.nodes[node_id]["cov"] == (4 / 21)

    for node_id in ("4", "-4"):
        assert digraph.nodes[node_id]["length"] == 7
        assert digraph.nodes[node_id]["gc_content"] == (2 / 7)
        assert digraph.nodes[node_id]["cov"] is None

    for node_id in ("5", "-5"):
        assert digraph.nodes[node_id]["length"] == 8
        assert digraph.nodes[node_id]["gc_content"] == (3 / 8)
        assert digraph.nodes[node_id]["cov"] is None

    for node_id in ("6", "-6"):
        assert digraph.nodes[node_id]["length"] == 4
        assert digraph.nodes[node_id]["gc_content"] == 0.25
        assert digraph.nodes[node_id]["cov"] is None

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
    g, paths = parse_gfa("metagenomescope/tests/input/sample1.gfa")
    assert paths is None
    check_sample_gfa_digraph(g)


def test_parse_gfa2_good():
    g, paths = parse_gfa("metagenomescope/tests/input/sample2.gfa")
    assert paths is None
    check_sample_gfa_digraph(g)


def test_parse_self_implied_edge():
    """Uses loop.gfa (c/o Shaun Jackman) to test self-implied GFA edges.

    We define a "self-implied edge" as an edge whose complement is itself. An
    example of such an edge is 2+ -> 2- in loop.gfa; the complement of this
    edge is -(2-) -> -(2+), which is equal to 2+ -> 2- (my notation looks kind
    of silly but you get the idea).

    The expected behavior is that self-implied edges are only added to the
    assembly graph visualization once. This corroborates the visualization of
    loop.gfa in Shaun's repository containing it
    (https://github.com/sjackman/assembly-graph).
    """
    digraph, paths = parse_gfa("metagenomescope/tests/input/loop.gfa")
    assert paths is None
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
        "L	4	-	5	+	0M",
    ]


def test_parse_no_length_node():
    s1 = get_sample1_gfa()
    s1.pop(1)
    s1.insert(1, "S\t1\t*")
    run_tempfile_test(
        "gfa",
        s1,
        GraphParsingError,
        "Found a node without a specified length: 1",
    )

    # Manually assigning node 1 a sequence should fix the problem
    # (since the length is then implied)
    s1.pop(1)
    s1.insert(1, "S\t1\tAAA")
    digraph, paths = run_tempfile_test("gfa", s1, None, None)
    assert paths is None
    assert digraph.nodes["1"]["gc_content"] == 0
    assert digraph.nodes["1"]["length"] == 3

    # Similarly, explicitly giving node 1 a length should also be ok
    # (for reference, see
    # https://github.com/GFA-spec/GFA-spec/blob/master/GFA1.md#optional-fields-2)
    s1.pop(1)
    s1.insert(1, "S\t1\t*\tLN:i:6")
    digraph, paths = run_tempfile_test("gfa", s1, None, None)
    assert paths is None
    assert digraph.nodes["1"]["gc_content"] is None
    assert digraph.nodes["1"]["length"] == 6

    # test super weird corner case where both forms of length are given, but
    # they disagree -- should be caught by gfapy
    s1.pop(1)
    s1.insert(1, "S\t1\tATCA\tLN:i:6")
    run_tempfile_test(
        "gfa",
        s1,
        InconsistencyError,
        "Length in LN tag (6) is different from length of sequence field (4)",
    )


def test_parse_invalid_id_node():
    s1 = get_sample1_gfa()
    # Evil hack to replace the two lines referring to node 1 to refer instead
    # to node "-1"
    for line_num in (1, 7):
        line = s1.pop(line_num)
        line = line.replace("1", "-1")
        s1.insert(line_num, line)
    run_tempfile_test(
        "gfa",
        s1,
        GraphParsingError,
        "Node IDs in the input assembly graph cannot "
        f'start with the "{config.REV}" character.',
    )


def test_parse_paths_and_containments_gfa1():
    g, paths = parse_gfa("metagenomescope/tests/input/all_line_types.gfa1.gfa")
    assert len(g.nodes) == 18
    # 4 links, 2 containments (times two for the RCs)
    # but for now we ignore containments!
    assert len(g.edges) == 8
    assert len(paths) == 4
    assert paths == {
        "14": ["11", "12"],
        "15": ["11", "13"],
        "-14": ["-12", "-11"],
        "-15": ["-13", "-11"],
    }
    exp_containment_edges = ("1", "5"), ("2", "6"), ("-5", "-1"), ("-6", "-2")
    for e in g.edges():
        assert (e[0], e[1]) not in exp_containment_edges


def test_parse_paths_and_containments_gfa2():
    g, paths = parse_gfa("metagenomescope/tests/input/all_line_types.gfa2.gfa")
    assert len(g.nodes) == 18
    # 4 links, 2 containments (times two for the RCs)
    # note that links and containments are all E-lines in GFA2 but thankfully
    # gfapy can distinguish them
    assert len(g.edges) == 8
    assert len(paths) == 4
    assert paths == {
        "14": ["11", "12"],
        "15": ["11", "13"],
        "-14": ["-12", "-11"],
        "-15": ["-13", "-11"],
    }
    exp_containment_edges = ("5", "1"), ("6", "2"), ("-1", "-5"), ("-2", "-6")
    for e in g.edges():
        assert (e[0], e[1]) not in exp_containment_edges


def test_parse_path_with_plus_and_minus():
    s1 = get_sample1_gfa()
    s1.append("P\tpath1\t3+,4-\t*")
    g, paths = run_tempfile_test("gfa", s1, None, None)
    assert len(paths) == 2
    assert paths == {"path1": ["3", "-4"], "-path1": ["4", "-3"]}


def test_parse_path_duplicate_name():
    s1 = get_sample1_gfa()
    s1.append("P\tpath1\t3+,4-\t*")
    s1.append("P\tpath1\t1+,2+\t*")
    run_tempfile_test("gfa", s1, NotUniqueError, "Line or ID not unique")


def test_parse_path_duplicate_name_of_rc():
    s1 = get_sample1_gfa()
    s1.append("P\tpath1\t3+,4-\t*")
    s1.append("P\t-path1\t1+,2+\t*")
    run_tempfile_test(
        "gfa", s1, GraphParsingError, "Duplicate path ID: -path1"
    )


def test_parse_path_of_just_edges_has_nodes_extracted():
    g, paths = parse_gfa("metagenomescope/tests/input/path_of_edges.gfa")
    assert len(g.nodes) == 6
    assert len(g.edges) == 4
    assert paths == {"15": ["1", "3", "4"], "-15": ["-4", "-3", "-1"]}


def test_multigraphs_okay_gfa1():
    s1 = get_sample1_gfa()
    s1.append("L\t1\t+\t2\t+\t10M")
    g, paths = run_tempfile_test("gfa", s1, None, None)
    assert paths is None
    assert len(g.edges) == 10
    assert ("1", "2", 0) in g.edges
    assert ("1", "2", 1) in g.edges
    assert ("-2", "-1", 0) in g.edges
    assert ("-2", "-1", 1) in g.edges


def test_multigraphs_okay_gfa2():
    g, paths = parse_gfa(
        "metagenomescope/tests/input/path_of_edges_multigraph.gfa"
    )
    assert len(g.nodes) == 6
    assert len(g.edges) == 6
    assert paths == {"15": ["1", "3", "4"], "-15": ["-4", "-3", "-1"]}
    assert ("1", "3", 0) in g.edges
    assert ("1", "3", 1) in g.edges
    assert ("-3", "-1", 0) in g.edges
    assert ("-3", "-1", 1) in g.edges
