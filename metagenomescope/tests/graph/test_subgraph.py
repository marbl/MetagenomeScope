import pytest
from metagenomescope import ui_config, cy_config
from metagenomescope.graph import (
    AssemblyGraph,
    Subgraph,
    DecoupledSubgraph,
    PatternStats,
)
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

    # Subgraph defaults to the graph being node-centric with lengths
    # stored in a "length" field. this default is mostly there so i don't
    # have to go back and fix a zillion tests.
    assert sg.node_centric
    assert sg.length_field == "length"
    assert sg.total_length == 116
    assert sg.record_node_names
    assert sg.min_name == "1"
    assert sg.count_positive_names
    assert sg.num_positive_names == 6


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
        # this is a GML file so no need to count positive node names
        # (like you could leave this set to True but it would just be
        # unnecessary and waste a tiny bit of time counting stuff)
        count_positive_names=False,
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

    # split nodes shouldn't break this! each full node is counted once towards
    # the length, and there are 12 full nodes, and each has length 1 bp, so
    # the total length should be 12 bp.
    assert sg.node_centric
    assert sg.length_field == "length"
    assert sg.total_length == 12

    # we didn't bother counting this, so it should be left at 0
    assert not sg.count_positive_names
    assert sg.num_positive_names == 0


def test_subgraph_flye_dot():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")

    sg = Subgraph(
        99999,
        "idk dude",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
        node_centric=False,
        length_field="approx_length",
        # record EDGE names instead since this is a Flye DOT graph
        record_node_names=False,
    )

    # just verify that this stuff didn't get broken ...
    assert not sg.node_centric
    assert sg.length_field == "approx_length"
    assert sg.total_length == 55000

    assert sg.count_positive_names
    # this graph will have a fake edge in it; it shouldn't influence this!
    # Also, this should only count one of the pair of {e9, -e9}.
    assert sg.num_positive_names == 10


def test_subgraph_missing_length_field_edge():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")

    # incorrect b/c this says the graph is node-centric and that the length
    # field is "length"
    with pytest.raises(WeirdError) as ei:
        Subgraph(
            456,
            "subgraph456",
            ag.nodeid2obj.values(),
            ag.edgeid2obj.values(),
            ag.pattid2obj.values(),
            node_centric=True,
            length_field="length",
        )
    assert 'has no field "length"?' in str(ei.value)

    # correctly says that the graph is not node-centric, but still incorrect
    # because the lengths for Flye DOT files are in "approx_length" and not
    # "length"
    with pytest.raises(WeirdError) as ei:
        Subgraph(
            456,
            "subgraph456",
            ag.nodeid2obj.values(),
            ag.edgeid2obj.values(),
            ag.pattid2obj.values(),
            node_centric=False,
            length_field="length",
        )
    assert 'has no field "length"?' in str(ei.value)


def test_subgraph_missing_length_field_node():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(WeirdError) as ei:
        Subgraph(
            456,
            "subgraph456",
            ag.nodeid2obj.values(),
            ag.edgeid2obj.values(),
            ag.pattid2obj.values(),
            node_centric=False,
            length_field="flumbity",
        )
    assert 'has no field "flumbity"?' in str(ei.value)

    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(WeirdError) as ei:
        Subgraph(
            456,
            "subgraph456",
            ag.nodeid2obj.values(),
            ag.edgeid2obj.values(),
            ag.pattid2obj.values(),
            node_centric=True,
            length_field="bumbity",
        )
    # people around the world are asking this: does node have bumbity?
    # inquiring minds would like to know
    assert 'has no field "bumbity"?' in str(ei.value)


def test_subgraph_repr():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")

    sg = Subgraph(
        99999,
        "SubgraphYeehaw",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
        node_centric=False,
        length_field="approx_length",
    )
    assert repr(sg) == (
        "SubgraphYeehaw (11 nodes; 12 edges; 3 patterns; length 55,000)"
    )


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


def test_decouple_already_done():
    # On initialization, the AssemblyGraph should already have called
    # decouple() where applicable
    ag = AssemblyGraph("metagenomescope/tests/input/simple-strand-tangled.gfa")
    assert len(ag.components) == 1
    with pytest.raises(WeirdError) as ei:
        ag.components[0].decouple(ag.graph, ag.nodename2objs)
    assert "is already decoupled" in str(ei.value)


def test_decouple_one_node_cc():
    # We already test this in tests/graph/assembly_graph/test_decoupling.py,
    # but we DON'T test what happens if you skip the AssemblyGraph validation
    # and force-call .decouple() on a one-node component. (The answer is that
    # it checks there that the component has <= 1 node and quits.)
    # Maybe checking this twice is overkill but whatever let's be safe
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # the smallest two components in sample1.gfa are one node each
    cc = ag.components[-1]
    assert len(cc.nodes) == 1
    assert not cc.decouple(ag.graph, ag.nodename2objs)
    assert not cc.decoupling_done


def test_to_cyjs_decoupled_but_not_in_scope_settings():
    # Although the only cc in this graph is strand-tangled, if the scope
    # settings don't call for decoupling then we should still draw the
    # full "doubled" graph
    ag = AssemblyGraph("metagenomescope/tests/input/simple-strand-tangled.gfa")
    assert len(ag.components) == 1
    cc = ag.components[0]
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS],
        [],
        ui_config.LAYOUT_DAGRE,
        {},
    )
    assert len(dr.region2layout) == 1
    # because we specified layout with dagre, layout will be done in the JS.
    # There won't be an actual python Layout object, then.
    assert dr.region2layout[cc] is None

    cyjs = dr.pack()
    drawn_ids = []
    node_ct = 0
    edge_ct = 0
    patt_ct = 0
    # without decoupling, should be 6 nodes, 6 edges, and 2 patts (bub & chain)
    assert len(cyjs) == 14
    for ele in cyjs:
        assert "data" in ele
        # due to historical reasons and/or me from 10 months ago being silly,
        # nodes/patterns have "id"s while edges have "uid"s
        has_id = "id" in ele["data"]
        has_uid = "uid" in ele["data"]
        assert has_id or has_uid
        # Use XOR - only one should be true
        assert has_id ^ has_uid
        if has_id:
            # this is a node / pattern
            drawn_ids.append(ele["data"]["id"])
            assert "ntype" in ele["data"]
            if ele["data"]["ntype"] == cy_config.NODE_DATA_TYPE:
                node_ct += 1
            else:
                patt_ct += 1
        else:
            # this is an edge
            assert "source" in ele["data"]
            assert "target" in ele["data"]
            drawn_ids.append(ele["data"]["uid"])
            edge_ct += 1

    # IDs should be unique ...
    assert len(drawn_ids) == len(set(drawn_ids))
    assert len(drawn_ids) == 14
    assert node_ct == 6
    assert edge_ct == 6
    assert patt_ct == 2


def test_to_cyjs_decoupled():
    # okay, NOW we can see what happens in the decoupled drawing
    ag = AssemblyGraph("metagenomescope/tests/input/simple-strand-tangled.gfa")
    assert len(ag.components) == 1
    cc = ag.components[0]
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS, ui_config.DECOUPLE],
        [],
        ui_config.LAYOUT_DAGRE,
        {},
    )
    assert len(dr.region2layout) == 1
    decoupled_subgraph = list(dr.region2layout.keys())[0]
    assert type(decoupled_subgraph) is DecoupledSubgraph
    assert dr.region2layout[decoupled_subgraph] is None
    assert decoupled_subgraph.cc_num == 1
    assert len(decoupled_subgraph.nodes) == 3
    assert len(decoupled_subgraph.edges) == 3
    assert len(decoupled_subgraph.patterns) == 0

    # lazy way of ensuring that there is just a single invalidated edge
    inval_edges = []
    for e in decoupled_subgraph.edges:
        if hasattr(e, "inval_type"):
            inval_edges.append(e)
    assert len(inval_edges) == 1

    cyjs = dr.pack()
    drawn_ids = []
    node_ct = 0
    edge_ct = 0
    patt_ct = 0
    # WITH decoupling, should be 3 nodes, 3 edges, and 0 patts.
    # (no patterns are drawn because not all children of either of the patterns
    # are shown in this scope)
    assert len(cyjs) == 6
    for ele in cyjs:
        assert "data" in ele
        has_id = "id" in ele["data"]
        has_uid = "uid" in ele["data"]
        assert has_id or has_uid
        assert has_id ^ has_uid
        if has_id:
            drawn_ids.append(ele["data"]["id"])
            assert "ntype" in ele["data"]
            if ele["data"]["ntype"] == cy_config.NODE_DATA_TYPE:
                node_ct += 1
            else:
                patt_ct += 1
        else:
            assert "source" in ele["data"]
            assert "target" in ele["data"]
            drawn_ids.append(ele["data"]["uid"])
            edge_ct += 1

    assert len(drawn_ids) == len(set(drawn_ids))
    assert len(drawn_ids) == 6
    assert node_ct == 3
    assert edge_ct == 3
    assert patt_ct == 0


def test_decoupled_subgraph_from_nondecoupled():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    cc = ag.components[0]
    with pytest.raises(WeirdError) as ei:
        DecoupledSubgraph(cc)
    assert "not decoupled?" in str(ei.value)


def test_decouple_non_cc_subgraph_currently_fails():
    # MAYBE we'll support it eventually. for now no way is it worth da trouble
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    sg = Subgraph(
        123,
        "subgraph123",
        ag.nodeid2obj.values(),
        ag.edgeid2obj.values(),
        ag.pattid2obj.values(),
    )
    with pytest.raises(WeirdError) as ei:
        sg.decouple(ag.graph, ag.nodename2objs)
    assert str(ei.value) == "Decoupling not currently supported for non-CCs"
