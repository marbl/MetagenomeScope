import networkx as nx
from metagenomescope.assembly_graph_parser import parse_dot


def test_parse_flye_yeast_good():
    """Tests that we can parse Flye DOT files."""
    g = parse_dot("metagenomescope/tests/input/flye_yeast.gv")
    assert type(g) is nx.MultiDiGraph
    # Make sure that the appropriate amounts of nodes and edges are read.
    #
    # (Note for future me: in flye_yeast.gv, nodes are not necessarily declared
    # on separate lines -- a lot of nodes in the file don't have their own
    # '"nodename" [style = "filled", fillcolor = "grey"];' line. This is fine,
    # since we delegate parsing the initial DOT file to NetworkX, and it
    # understands this. However, if you are just counting all of the
    # occurrences of "filled" in flye_yeast.gv and are confused about why 24
    # such occurrences (but nonetheless 61 nodes total), this is why.)
    assert len(g.nodes) == 61
    assert len(g.edges) == 122

    # Ensure that parallel / duplicate / whatever-you-call-them edges are
    # respected. One good example of this: there should be 7 distinct edges
    # from node 1 --> node 35
    assert g.number_of_edges("1", "35") == 7
    # The order shouldn't be arbitrary here, I think, since NetworkX should be
    # parsing these in line order (starting from the top). This might change,
    # in which case we'd need to update this test. (So hey, if it's like 2053
    # and this test begins failing right *here*, now you know why...)
    assert g.adj["1"]["35"][0] == {
        "color": "black",
        "id": "-7",
        "approx_length": 171000.0,
        "cov": 79,
    }
    assert g.adj["1"]["35"][1] == {
        "color": "black",
        "id": "-10",
        "approx_length": 720000.0,
        "cov": 80,
    }
    assert g.adj["1"]["35"][2] == {
        "color": "black",
        "id": "18",
        "approx_length": 519000.0,
        "cov": 77,
    }
    assert g.adj["1"]["35"][3] == {
        "color": "black",
        "id": "-12",
        "approx_length": 117000.0,
        "cov": 69,
    }
    assert g.adj["1"]["35"][4] == {
        "color": "black",
        "id": "36",
        "approx_length": 171000.0,
        "cov": 78,
    }
    assert g.adj["1"]["35"][5] == {
        "color": "red",
        "id": "-37",
        "approx_length": 5000.0,
        "cov": 269,
    }
    assert g.adj["1"]["35"][6] == {
        "color": "black",
        "id": "-38",
        "approx_length": 426000.0,
        "cov": 83,
    }

    # Make sure that optional attributes (for flye graphs, "dir") are
    # respected. There are just two edges that look like this.
    #
    # (there's only one edge from 54 -> 55 in this graph, so its key is 0)
    assert g.edges["54", "55", 0] == {
        "color": "goldenrod",
        "id": "50",
        "approx_length": 1800,
        "cov": 202,
        "dir": "both",
    }
    # (there are five edges from 35 -> 35 in this graph; the one with dir=both
    # has the bottom-most line out of all of those edge declarations in the DOT
    # file, so it gets the final key of 4 [these keys are 0-indexed, if you
    # didn't figure that out yet])
    assert g.edges["35", "35", 4] == {
        "color": "red",
        "id": "57",
        "approx_length": 500,
        "cov": 77078,
        "dir": "both",
    }
