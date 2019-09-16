import pytest
from metagenomescope.assembly_graph_parser import sniff_filetype, is_not_pos_int


def test_is_not_pos_int():
    assert is_not_pos_int("-3")
    assert is_not_pos_int("-3.0")
    assert is_not_pos_int("3.0")
    assert is_not_pos_int("ABC")
    assert is_not_pos_int("0x123")
    assert is_not_pos_int("0")
    assert is_not_pos_int("0.0")
    assert is_not_pos_int("5.6")
    assert is_not_pos_int("5 6")
    assert is_not_pos_int("5/6")
    assert is_not_pos_int("6/6")
    assert is_not_pos_int("12345.6789")
    assert is_not_pos_int("-50000")
    assert is_not_pos_int("---50000")
    assert not is_not_pos_int("5")
    assert not is_not_pos_int("3")
    assert not is_not_pos_int("1")
    assert not is_not_pos_int("50000")
    assert not is_not_pos_int("12345")


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
    assert sniff_filetype("LastGraphfastg") == "fastg"

    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf.asdf")
    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf")


# def test_assemblygraph_constructor_and_sniff_filetype():
#     velvet_g = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
#
#     gml_g = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
#
#     gfa_g = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
#
#     with pytest.raises(NotImplementedError):
#         AssemblyGraph("metagenomescope/tests/input/garbage.thing")
