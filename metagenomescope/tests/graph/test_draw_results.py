import pytest
from metagenomescope.graph import DrawResults, Subgraph, Node, Edge
from metagenomescope import ui_config, config
from metagenomescope.errors import WeirdError


def test_init_empty():
    dr = DrawResults({}, [ui_config.SHOW_PATTERNS])
    assert dr.region2layout == {}
    assert dr.draw_settings == [ui_config.SHOW_PATTERNS]
    assert dr.incl_patterns
    assert dr.layouts_given
    assert dr.num_full_nodes == 0
    assert dr.num_real_edges == 0
    assert dr.num_patterns == 0


def test_init_nolayout_subgraph():
    b = Node(0, "B", {"orientation": config.FWD})
    sg = Subgraph(5, "sg5", [b], [], [])
    dr = DrawResults({sg: None}, [])
    assert dr.region2layout == {sg: None}
    assert dr.draw_settings == []
    assert not dr.incl_patterns
    assert not dr.layouts_given
    assert dr.num_full_nodes == 1
    assert dr.num_real_edges == 0
    assert dr.num_patterns == 0


def test_get_fancy_count_text():
    b = Node(0, "B", {"orientation": config.FWD})
    sg = Subgraph(5, "sg5", [b], [], [])
    dr = DrawResults({sg: None}, [])
    assert dr.get_fancy_count_text() == "1 node, 0 edges, 0 patterns"


def test_repr():
    b = Node(0, "B", {"orientation": config.FWD})
    e = Edge(8, 0, 0, {})
    e2 = Edge(9, 0, 0, {"asdf": "ghjik"})
    sg = Subgraph(5, "sg5", [b], [e, e2], [])
    dr = DrawResults({sg: None}, [])
    assert (
        repr(dr) == "DrawResults(1 region (1 node, 2 edges, 0 patterns); [])"
    )


def test_get_node_and_edge_ids():
    b = Node(0, "B", {"orientation": config.FWD})
    e = Edge(8, 0, 0, {})
    e2 = Edge(9, 0, 0, {"asdf": "ghjik"})
    sg = Subgraph(5, "sg5", [b], [e, e2], [])
    dr = DrawResults({sg: None}, [])
    nodeids, edgeids = dr.get_node_and_edge_ids()
    assert nodeids == [0]
    # order is arbitrary here
    assert sorted(edgeids) == [8, 9]


def test_add_simple():
    b = Node(0, "B", {"orientation": config.FWD})
    sg5 = Subgraph(5, "sg5", [b], [], [])

    c = Node(0, "C", {"orientation": config.REV})
    sg6 = Subgraph(6, "sg6", [c], [], [])

    dr = DrawResults({sg5: None}, [])
    dr2 = DrawResults({sg6: None}, [])
    drs = dr + dr2
    assert drs.region2layout == {sg5: None, sg6: None}
    assert drs.draw_settings == []


def test_add_with_draw_settings():
    b = Node(0, "B", {"orientation": config.FWD})
    sg5 = Subgraph(5, "sg5", [b], [], [])

    c = Node(0, "C", {"orientation": config.REV})
    sg6 = Subgraph(6, "sg6", [c], [], [])

    dr = DrawResults({sg5: None}, [ui_config.SHOW_PATTERNS])
    dr2 = DrawResults({sg6: None}, [ui_config.SHOW_PATTERNS])
    drs = dr + dr2
    assert drs.region2layout == {sg5: None, sg6: None}
    assert drs.draw_settings == [ui_config.SHOW_PATTERNS]


def test_add_duplicate_region():
    b = Node(0, "B", {"orientation": config.FWD})
    sg5 = Subgraph(5, "sg5", [b], [], [])

    dr = DrawResults({sg5: None}, [])
    dr2 = DrawResults({sg5: None}, [])
    with pytest.raises(WeirdError) as ei:
        dr + dr2
    assert "Regions present in multiple DrawResults" in str(ei.value)


def test_add_incompatible_draw_settings():
    b = Node(0, "B", {"orientation": config.FWD})
    sg5 = Subgraph(5, "sg5", [b], [], [])

    c = Node(0, "C", {"orientation": config.REV})
    sg6 = Subgraph(6, "sg6", [c], [], [])

    dr = DrawResults({sg5: None}, [ui_config.SHOW_PATTERNS])
    dr2 = DrawResults({sg6: None}, [])
    with pytest.raises(WeirdError) as ei:
        dr + dr2
    assert "Incompatible draw settings" in str(ei.value)
