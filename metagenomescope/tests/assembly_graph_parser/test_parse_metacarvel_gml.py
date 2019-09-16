import pytest
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


def test_parse_metacarvel_gml_no_labels():
    """TODO: do these using tmpfiles"""
