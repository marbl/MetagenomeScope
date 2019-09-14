from metagenomescope.assembly_graph_parser import (
    sniff_filetype,
    parse_lastgraph,
)


def test_parse_lastgraph():
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


def test_sniff_filetype():
    assert sniff_filetype("asdf.lastgraph") == "lastgraph"
    assert sniff_filetype("asdf.LASTGRAPH") == "lastgraph"
    assert sniff_filetype("asdf_LastGraph") == "lastgraph"
    assert sniff_filetype("asdf.LastGraph") == "lastgraph"
    assert sniff_filetype("gml_LastGraph") == "lastgraph"

    assert sniff_filetype("asdf.gml") == "gml"
    assert sniff_filetype("asdf.GML") == "gml"
    assert sniff_filetype("asdf_gml") == "gml"
    assert sniff_filetype("asdf.gmL") == "gml"
    assert sniff_filetype("gfa_gmL") == "gml"

    assert sniff_filetype("asdf.gfa") == "gfa"
    assert sniff_filetype("asdf.GFA") == "gfa"
    assert sniff_filetype("asdf_gfa") == "gfa"
    assert sniff_filetype("asdf.GfA") == "gfa"
    assert sniff_filetype("fastg_gFa") == "gfa"

    assert sniff_filetype("asdf.fastg") == "fastg"
    assert sniff_filetype("asdf.FASTG") == "fastg"
    assert sniff_filetype("asdf_fastg") == "fastg"
    assert sniff_filetype("aSdF.FaStG") == "fastg"
    assert sniff_filetype("LastGraph_fastg") == "fastg"


# def test_assemblygraph_constructor_and_sniff_filetype():
#     velvet_g = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
#
#     gml_g = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
#
#     gfa_g = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
#
#     with pytest.raises(NotImplementedError):
#         AssemblyGraph("metagenomescope/tests/input/garbage.thing")
