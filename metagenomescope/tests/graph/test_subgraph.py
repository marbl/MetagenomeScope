import pytest
from metagenomescope import ui_config
from metagenomescope.graph import AssemblyGraph, Subgraph, PatternStats
from metagenomescope.errors import WeirdError
from metagenomescope.tests.layout import utils as layout_test_utils


def test_subgraph_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    sg = Subgraph(
        123,
        "subgraph123",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    assert sg.unique_id == 123
    assert sg.name == "subgraph123"

    assert sg.num_unsplit_nodes == 12
    assert sg.num_split_nodes == 0
    assert sg.num_total_nodes == 12
    assert sg.num_full_nodes == 12

    assert sg.num_real_edges == 8
    assert sg.num_fake_edges == 0
    assert sg.num_total_edges == 8
    assert sg.pattern_stats == PatternStats(num_chains=2)


def test_subgraph_nested_patterns():
    """Tests that nested patterns are processed correctly.

    Previous versions of Subgraph initialization exploded when you used
    nested patterns, due to trying to recursively add in descendants of
    input patterns while ALSO adding all nodes/edges up front. So there
    would be like hundreds of edges unnecessarily lol.

    See https://github.com/marbl/MetagenomeScope/issues/320 wrt the
    attendant pain and suffering that this test should ward us against.
    """
    # see test_bubble_cyclic_chain_identification() in the AsmGraph
    # hierarch decomp tests for a pretty figure of this graph
    # APPRECIATE MY ASCII ART LOL
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )

    sg = Subgraph(
        456,
        "subgraph456",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    assert sg.unique_id == 456
    assert sg.name == "subgraph456"

    assert sg.num_unsplit_nodes == 8
    assert sg.num_split_nodes == 8
    assert sg.num_total_nodes == 16
    assert sg.num_full_nodes == 12

    assert sg.num_real_edges == 16
    assert sg.num_fake_edges == 4
    assert sg.num_total_edges == 20
    assert sg.pattern_stats == PatternStats(num_bubbles=4, num_cyclicchains=1)


def test_subgraph_count_positive_full_nodes():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )

    sg = Subgraph(
        456,
        "subgraph456",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )

    assert sg.count_positive_full_nodes() == 12


def test_subgraph_count_positive_real_edges():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")

    sg = Subgraph(
        99999,
        "idk dude",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    # this graph will have a fake edge in it; it shouldn't influence this!
    # Also, this should only count one of the pair of {e9, -e9}.
    assert sg.count_positive_real_edges() == 10


def test_subgraph_count_positive_real_edges_when_no_userspecified_edgeids():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/bubble_cyclic_chain_test.gml"
    )

    sg = Subgraph(
        456,
        "subgraph456",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )

    with pytest.raises(WeirdError) as ei:
        sg.count_positive_real_edges()
    assert "No 'id' field" in str(ei.value)


def test_subgraph_repr():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")

    sg = Subgraph(
        99999,
        "SubgraphYeehaw",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    assert repr(sg) == "SubgraphYeehaw (11 nodes, 12 edges, 3 patterns)"


def test_to_cyjs_clientside_layout():
    """When the layout algorithm isn't a Graphviz program, we'll do layout
    in the client side -- so the Layout object should be None."""
    _, cc, _, _, _ = layout_test_utils.get_cycle_with_tip_data()
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS],
        [],
        ui_config.LAYOUT_DAGRE,
        {},
    )
    assert len(dr.region2layout) == 1
    lay = dr.region2layout[cc]
    assert lay is None


def test_to_cyjs_gv_layout():
    ag, cc, n1, n2, n3 = layout_test_utils.get_cycle_with_tip_data()
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS],
        [],
        ui_config.LAYOUT_DOT,
        {ui_config.LAYOUT_DOT: {"ranksep": 3}},
    )
    assert len(dr.region2layout) == 1
    lay = dr.region2layout[cc]
    assert lay is not None
    layout_test_utils.check_layout_cycle_with_tip(ag, lay, n1, n2, n3)
