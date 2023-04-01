import networkx as nx
from metagenomescope.assembly_graph_parser import parse_dot
from metagenomescope.errors import GraphParsingError
from .utils import run_tempfile_test


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


def test_parse_mixed_edge_type():
    # NOTE: if we eventually add in support for non-Flye/LJA DOT files (e.g.
    # where we only parse the topology of the graph's nodes/edges, and ignore
    # other stuff), then these graphs should of course be supported.

    # The cases of (Flye edge, then LJA edge) and vice versa trigger different
    # sanity checks, so hit both of them.

    # First: Flye edge, then LJA edge
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [label = "id -5\\l6k 777x", color = "red", penwidth = 3];',
            '2 -> 3 [color = "black", label="A99(2)"];',
            "}",
        ],
        GraphParsingError,
        (
            "Edge 2 -> 3 looks like it came from LJA, but other edge(s) in "
            "the same file look like they came from Flye?"
        ),
    )

    # Second: LJA edge, then Flye edge
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '2 -> 3 [color = "black", label="A99(2)"];',
            '1 -> 2 [label = "id -5\\l6k 777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        (
            "Edge 1 -> 2 looks like it came from Flye, but other edge(s) in "
            "the same file look like they came from LJA?"
        ),
    )

    # Paranoid extra check: two LJA edges, then a Flye edge
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '3 -> 4 [color = "black", label="C99(2)"];',
            '2 -> 3 [color = "black", label="A99(2)"];',
            '1 -> 2 [label = "id -5\\l6k 777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        (
            "Edge 1 -> 2 looks like it came from Flye, but other edge(s) in "
            "the same file look like they came from LJA?"
        ),
    )


def test_parse_nolabel_edge():
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [color = "red", penwidth = 3];',
            '2 -> 3 [color = "black", label="A99(2)"];',
            "}",
        ],
        GraphParsingError,
        (
            "Edge 1 -> 2 has no label. Note that we currently only accept "
            "DOT files from Flye or LJA."
        ),
    )


def test_parse_flye_label_no_backslash_ell():
    # \n instead of \l
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [label = "id -5\n6k 777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        "Edge 1 -> 2 has a label containing zero '\\l' separators?",
    )
    # No newlines at all
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '100 -> 200 [label = "id -5 6k 777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        "Edge 100 -> 200 has a label containing zero '\\l' separators?",
    )


def test_parse_flye_label_many_backslash_ells():
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [label = "id -5\\l6k\\l777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        "Edge 1 -> 2 has a label containing more than one '\\l' separator?",
    )


def test_parse_flye_label_bad_id_line():
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [label = "idee -5\\l6k 777x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        # i feel like this error message, as it is currently, is not my best
        # work, and i don't wanna tie myself to it in this test. so let's just
        # make sure the first sentence of this error message gets thrown. (lol)
        'Edge 1 -> 2 has a label with a first line of "idee -5".',
    )


def test_parse_flye_duplicate_edge_ids():
    run_tempfile_test(
        "gv",
        [
            "digraph g {",
            '1 -> 2 [label = "id -5\\l6k 777x", color = "red", penwidth = 3];',
            '2 -> 3 [label = "id -5\\l7k 888x", color = "red", penwidth = 3];',
            "}",
        ],
        GraphParsingError,
        (
            "Edge 2 -> 3 has the ID -5, but other edge(s) in this file have "
            "the same ID."
        )
    )
