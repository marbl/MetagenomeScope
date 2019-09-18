# from .utils import run_tempfile_test
from metagenomescope.input_node_utils import negate_node_id
from metagenomescope.assembly_graph_parser import parse_gfa


def test_parse_gfa1_good():
    digraph = parse_gfa("metagenomescope/tests/input/sample1.gfa")
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
