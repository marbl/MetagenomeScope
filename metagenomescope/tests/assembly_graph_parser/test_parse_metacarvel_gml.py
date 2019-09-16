from networkx import NetworkXError
from .utils import run_tempfile_test
from metagenomescope.assembly_graph_parser import parse_metacarvel_gml


def test_parse_metacarvel_gml_good():
    """Tests that MetaCarvel GMLs are parsed correctly, using the MaryGold
    fig. 2a graph as an example.

    The bulk of work in GML parsing is done using NetworkX's read_gml()
    function, so we don't test this super thoroughly. Mostly, we just verify
    that all of the graph attributes are being read correctly here.

    A pleasant thing about this graph is that one of the nodes (NODE_3) has a
    different orientation than the others. This slight difference lends itself
    well to writing mostly-simple tests that can still check to make sure
    details are being processed as expected.
    """
    digraph = parse_metacarvel_gml(
        "metagenomescope/tests/input/marygold_fig2a.gml"
    )
    # Make sure that the appropriate amounts of nodes and edges are read
    assert len(digraph.nodes) == 12
    assert len(digraph.edges) == 16
    for i in range(1, 13):
        label = "NODE_{}".format(i)
        if i == 3:
            assert digraph.nodes[label]["orientation"] == "REV"
        else:
            assert digraph.nodes[label]["orientation"] == "FOW"
        assert digraph.nodes[label]["length"] == "100"
        assert "id" not in digraph.nodes[label]
        assert "label" not in digraph.nodes[label]
    for e in digraph.edges:
        if e == ("NODE_3", "NODE_5"):
            assert digraph.edges[e]["orientation"] == "BB"
        elif e == ("NODE_1", "NODE_3"):
            assert digraph.edges[e]["orientation"] == "EE"
        else:
            assert digraph.edges[e]["orientation"] == "EB"
        assert digraph.edges[e]["mean"] == "-200.00"
        assert digraph.edges[e]["stdev"] == 25.1234
        assert digraph.edges[e]["bsize"] == 30

    # TODO add various bad-GML parsing tests
    # - Graph with no labels (nx should nuke this)
    # - Graph with insufficient node metadata (caught in parse_metacarvel_gml)
    # - Graph with insufficient edge metadata (caught in parse_metacarvel_gml)
    # - Graph with duplicate edges and is multigraph (caught in parse_metacarvel_gml)
    # - Graph with duplicate edges and not multigraph (nx should nuke this)
    # - undirected graph (caught in parse_metacarvel_gml)


def get_marygold_gml():
    with open("metagenomescope/tests/input/marygold_fig2a.gml", "r") as mg:
        return mg.readlines()


def test_parse_metacarvel_gml_no_labels():
    """Tests parsing GMLs where a node doesn't have a label.

    NX should raise an error automatically in this case.
    """
    mg = get_marygold_gml()
    # Remove the fifth line (the one that defines a label for node 10)
    mg.pop(4)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'label' attribute", join_char=""
    )
    # Remove another label attribute, this time for node 6
    # (This label decl. is on line 17, and we use an index of 15 here due to
    # 0-indexing and then due to line 5 already being removed)
    mg.pop(15)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'label' attribute", join_char=""
    )


def test_parse_metacarvel_gml_no_ids():
    """Tests parsing GMLs where a node doesn't have an ID.

    NX should raise an error automatically in this case.
    """
    mg = get_marygold_gml()
    # Remove the fourth line (the one that defines an ID for node 10)
    mg.pop(3)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'id' attribute", join_char=""
    )
    # Remove another ID attribute, this time for node 1
    mg.pop(8)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'id' attribute", join_char=""
    )


def test_parse_metacarvel_gml_insufficient_node_metadata():
    """Tests parsing GMLs where nodes don't have orientation and/or length."""
    mg = get_marygold_gml()
    # Remove orientation from node 10
    mg.pop(5)
    run_tempfile_test(
        "gml",
        mg,
        ValueError,
        "Only 11 / 12 nodes have orientation given.",
        join_char="",
    )
