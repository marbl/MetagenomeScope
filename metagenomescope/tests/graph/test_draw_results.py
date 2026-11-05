from metagenomescope.graph import DrawResults, Subgraph, Component, Node, Edge
from metagenomescope import ui_config, config


def test_init_empty():
    dr = DrawResults({}, [ui_config.SHOW_PATTERNS], [ui_config.HCENTER])
    assert dr.region2layout == {}
    assert dr.scope_settings == [ui_config.SHOW_PATTERNS]
    assert dr.modifier_settings == [ui_config.HCENTER]
    assert dr.incl_patterns
    assert dr.layouts_given
    assert dr.num_full_nodes == 0
    assert dr.num_real_edges == 0
    assert dr.num_patterns == 0


def test_init_nolayout_subgraph():
    b = Node(0, "B", {"orientation": config.FWD, "length": 20})
    sg = Subgraph(5, "sg5", [b], [], [])
    dr = DrawResults({sg: None}, [], [])
    assert dr.region2layout == {sg: None}
    assert dr.scope_settings == []
    assert dr.modifier_settings == []
    assert not dr.incl_patterns
    assert not dr.layouts_given
    assert dr.num_full_nodes == 1
    assert dr.num_real_edges == 0
    assert dr.num_patterns == 0


def test_get_fancy_count_text():
    b = Node(0, "B", {"orientation": config.FWD, "length": 20})
    sg = Subgraph(5, "sg5", [b], [], [])
    dr = DrawResults({sg: None}, [], [])
    assert dr.get_fancy_count_text() == "1 node, 0 edges, 0 patterns"


def test_repr():
    b = Node(0, "B", {"orientation": config.FWD, "length": 20})
    e = Edge(8, 0, 0, {})
    e2 = Edge(9, 0, 0, {"asdf": "ghjik"})
    sg = Subgraph(5, "sg5", [b], [e, e2], [])
    dr = DrawResults({sg: None}, [], [])
    assert (
        repr(dr)
        == "DrawResults(1 region (1 node, 2 edges, 0 patterns); []; [])"
    )


def test_get_node_and_edge_ids():
    b = Node(0, "B", {"orientation": config.FWD, "length": 20})
    e = Edge(8, 0, 0, {})
    e2 = Edge(9, 0, 0, {"asdf": "ghjik"})
    sg = Subgraph(5, "sg5", [b], [e, e2], [])
    dr = DrawResults({sg: None}, [], [])
    nodeids, edgeids = dr.get_node_and_edge_ids()
    assert nodeids == [0]
    # order is arbitrary here
    assert sorted(edgeids) == [8, 9]


def test_get_sorted_regions_subgraphs():
    b = Node(0, "B", {"orientation": config.FWD, "length": 30})
    b2 = Node(1, "B2", {"orientation": config.FWD, "length": 30})
    sg5 = Subgraph(5, "sg5", [b, b2], [], [])

    c = Node(2, "C", {"orientation": config.REV, "length": 30})
    sg6 = Subgraph(6, "sg6", [c], [], [])

    dr = DrawResults({sg5: None, sg6: None}, [ui_config.SHOW_PATTERNS], [])

    assert dr.get_sorted_regions() == [sg5, sg6]


def test_get_sorted_regions_subgraphs_and_components():
    b = Node(0, "B", {"orientation": config.FWD, "length": 30})
    b2 = Node(1, "B2", {"orientation": config.FWD, "length": 30})
    sg5 = Subgraph(5, "sg5", [b, b2], [], [])

    c = Node(2, "C", {"orientation": config.REV, "length": 30})
    sg6 = Subgraph(6, "sg6", [c], [], [])

    n1 = Node(3, "1", {"length": 1})
    n2 = Node(4, "2", {"length": 1})
    n3 = Node(5, "3", {"length": 1})
    n4 = Node(6, "4", {"length": 1})
    sg7 = Subgraph(7, "sg7", [n1, n2, n3, n4], [], [])

    dr = DrawResults(
        {sg5: None, sg6: None, sg7: None}, [ui_config.SHOW_PATTERNS], []
    )
    assert dr.get_sorted_regions() == [sg7, sg5, sg6]

    r = Node(7, "5", {"length": 3})
    cc = Component(8, [r], [], [])

    # even though the component only has one node, it still goes before the
    # subgraphs in the ordering here (although this shouldn't really happen in
    # practice; see get_sorted_regions()'s docs for details)

    dr2 = DrawResults(
        {sg5: None, sg6: None, sg7: None, cc: None},
        [ui_config.SHOW_PATTERNS],
        [],
    )
    assert dr2.get_sorted_regions() == [cc, sg7, sg5, sg6]
