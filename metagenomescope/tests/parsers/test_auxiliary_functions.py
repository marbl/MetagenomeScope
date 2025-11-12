import networkx as nx
import pytest
from metagenomescope.parsers import (
    sniff_filetype,
    is_not_pos_int,
    make_multigraph_if_not_already,
)
from metagenomescope.errors import WeirdError


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

    # Now, repeat most of the tests above but with non-string ints/floats
    # (where applicable)
    # A few notes re: weird-looking cases:
    # 1. 6 / 6 is actually equal to 1.0 in Python (i.e. it's a float). That is,
    #    it's not an integer, even though yes ~~mathematically~~ it's equal to
    #    1.
    # 2. I was going to write a second note here but I forgot what it was while
    #    I was writing the first note. If anything here looks especially
    #    questionable to whoever is reading this, feel free to submit a PR ;)
    assert is_not_pos_int(-3)
    assert is_not_pos_int(-3.0)
    assert is_not_pos_int(3.0)
    assert is_not_pos_int(0)
    assert is_not_pos_int(0.0)
    assert is_not_pos_int(5 / 6)
    assert is_not_pos_int(6 / 6)
    assert is_not_pos_int(12345.6789)
    assert is_not_pos_int(-50000)
    assert not is_not_pos_int(5)
    assert not is_not_pos_int(3)
    assert not is_not_pos_int(1)
    assert not is_not_pos_int(50000)
    assert not is_not_pos_int(12345)


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

    assert sniff_filetype("asdf.dot") == "dot"
    assert sniff_filetype("ASDF.DOT") == "dot"
    assert sniff_filetype("asdf.gv") == "gv"
    assert sniff_filetype("ASDF.GV") == "gv"

    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf.asdf")
    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf")


def test_make_multigraph_if_not_already_conversion():
    g = nx.DiGraph()
    g.add_edge(5, 6)
    g.add_edge(5, 6)
    assert len(g.nodes) == 2
    # adding the same edge twice won't do anything
    assert len(g.edges) == 1

    m = make_multigraph_if_not_already(g)
    assert type(m) is nx.MultiDiGraph
    # of course, the structure of the graph is still the same. it's not like
    # networkx *knows* about the parallel edge that we tried to add earlier.
    assert len(m.nodes) == 2
    assert len(m.edges) == 1
    # ... but now, we can add parallel edges!
    m.add_edge(5, 6)
    assert len(m.nodes) == 2
    assert len(m.edges) == 2


def test_make_multigraph_if_not_already_no_conversion():
    g = nx.MultiDiGraph()
    g.add_edge(5, 6)
    g.add_edge(5, 6)
    assert len(g.nodes) == 2
    assert len(g.edges) == 2
    m = make_multigraph_if_not_already(g)
    assert type(m) is nx.MultiDiGraph
    assert g == m


def test_make_multigraph_if_not_already_bad_type_undirected():
    # construct an undirected graph
    g = nx.Graph()
    g.add_edge(5, 6)
    g.add_edge(5, 6)
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    with pytest.raises(WeirdError):
        make_multigraph_if_not_already(g)


def test_make_multigraph_if_not_already_bad_type_undirected_multigraph():
    # construct an undirected multigraph
    g = nx.MultiGraph()
    g.add_edge(5, 6)
    g.add_edge(5, 6)
    assert len(g.nodes) == 2
    assert len(g.edges) == 2
    with pytest.raises(WeirdError):
        make_multigraph_if_not_already(g)


def test_make_multigraph_if_not_already_bad_type_misc():
    with pytest.raises(WeirdError):
        make_multigraph_if_not_already("lol i'm evil")
