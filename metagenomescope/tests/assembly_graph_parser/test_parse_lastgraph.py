import os
import tempfile
import pytest
from metagenomescope.assembly_graph_parser import parse_lastgraph
from metagenomescope.tests.assembly_graph_parser.test_validate_lastgraph import (
    reset_glines,
)


def get_lastgraph_tempfile():
    """Creates a temporary file using tempfile.mkstemp().

    Returns the output of the mkstemp() call.
    """
    return tempfile.mkstemp(suffix=".LastGraph", text=True)


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


def test_parse_lastgraph_node_interrupted():
    glines = reset_glines()
    glines.pop(3)
    # CODELINK: Use of tempfile in this way is based on NetworkX's tests --
    # https://github.com/networkx/networkx/blob/master/networkx/readwrite/tests/test_gml.py.
    filehandle, filename = get_lastgraph_tempfile()
    try:
        with open(filename, "w") as f:
            f.write("\n".join(glines))
        with pytest.raises(ValueError) as ei:
            parse_lastgraph(filename)
        assert "Line 4: Node block ends too early." in str(ei.value)
    finally:
        os.close(filehandle)
        os.unlink(filename)
