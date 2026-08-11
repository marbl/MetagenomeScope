from collections import Counter
from metagenomescope import config, name_utils
from metagenomescope.graph import AssemblyGraph, graph_utils

# This stuff MIGHT be overengineered


def id2name(ag, i):
    return ag.nodeid2obj[i].name


def nodeids2names(ag, ids):
    return sorted([id2name(ag, i) for i in ids])


def edge2tuple(ag, eobj):
    return (id2name(ag, eobj.new_src_id), id2name(ag, eobj.new_tgt_id))


def edgeid2tuple(ag, i):
    eobj = ag.edgeid2obj[i]
    return edge2tuple(ag, eobj)


def edgeids2tuplectr(ag, ids):
    # Given a collection of edge IDs, returns a counter of (s, t) tuples
    # indicating -- for each pair of nodes (s, t) where there exist > 1 edges
    # -- how many edges there are from s to t
    return Counter(edgeid2tuple(ag, i) for i in ids)


def test_decouple_simple():
    # This is the example graph shown in
    # https://github.com/marbl/MetagenomeScope/issues/449
    ag = AssemblyGraph("metagenomescope/tests/input/simple-strand-tangled.gfa")
    assert len(ag.components) == 1
    cc = ag.components[0]
    assert cc.decoupling_done

    # In theory we could also validly decouple the graph in such a way that eg
    # node -2 instead of 2 is used, but because we use sorting in decouple()
    # this should make the choices of what nodes are shown deterministic
    assert nodeids2names(ag, cc.dc_shown_node_ids) == ["-3", "1", "2"]

    assert edgeids2tuplectr(ag, cc.dc_shown_edge_ids) == {
        ("-3", "1"): 1,
        ("1", "2"): 1,
    }

    assert len(cc.dc_inval_edges) == 1
    ie = cc.dc_inval_edges[0]
    # because this is an invalidated edge, either its source or its target (but
    # not both!) must be not shown in the decoupling. Here, this edge is really
    # from 2 -> -1, and -1 is not shown. This means that this has inval_type
    # INVAL_TGT, indicating that the target node is the one that's not shown.
    assert ie.inval_type == config.INVAL_TGT
    assert ie.ports == ("e", "e")
    assert id2name(ag, ie.rc_node_id) == "1"

    # Okay, so this edge looks from the outside like it is from 2 -> 1. This is
    # why it "just works" in Layout, DrawResults, etc.
    assert edge2tuple(ag, ie) == ("2", "1")
    # ... but it is actually representing the edge 2 -> -1!
    assert edge2tuple(ag, ie.e) == ("2", "-1")
    assert ie.rand_idx == ie.e.rand_idx
    assert ie.cc_num == ie.e.cc_num
    # parent ID shouldn't really matter for now -- invalidated edges shouldn't
    # have a parent since one of their nodes isn't drawn. but let's be super
    # careful i guess
    assert ie.parent_id == ie.e.parent_id


def test_decouple_parallel_inval_edges():
    # Make sure to set rmdup to RMDUP_NO to ensure that, even though this is
    # a GFA file, its parallel edges are kept.
    ag = AssemblyGraph(
        "metagenomescope/tests/input/parallel-strand-tangled.gfa",
        rmdup=config.RMDUP_NO,
    )
    assert len(ag.components) == 1
    cc = ag.components[0]
    assert cc.decoupling_done

    # Again, 1 and -1 are the highest-degree nodes. We should first set 1 as
    # "shown," then radiate out from there and set the orientations of other
    # shown nodes.
    assert nodeids2names(ag, cc.dc_shown_node_ids) == ["-3", "1", "2"]

    assert edgeids2tuplectr(ag, cc.dc_shown_edge_ids) == {
        ("-3", "1"): 1,
        ("1", "2"): 1,
    }

    assert len(cc.dc_inval_edges) == 2
    e0 = cc.dc_inval_edges[0]
    e1 = cc.dc_inval_edges[1]
    assert e0.inval_type == e1.inval_type == config.INVAL_TGT
    assert e0.ports == e1.ports == ("e", "e")
    assert id2name(ag, e0.rc_node_id) == id2name(ag, e1.rc_node_id) == "1"

    # as before, both of these edges should look like they're from 2 -> 1,
    # but they're actually representing 2 -> -1
    assert edge2tuple(ag, e0) == edge2tuple(ag, e1) == ("2", "1")
    assert edge2tuple(ag, e0.e) == edge2tuple(ag, e1.e) == ("2", "-1")
    # just clumsily testing that these edges and the edges that they are
    # representing look ok
    assert e0.rand_idx == e0.e.rand_idx
    assert e1.rand_idx == e1.e.rand_idx
    assert e0.cc_num == e0.e.cc_num
    assert e1.cc_num == e1.e.cc_num
    assert e0.parent_id == e0.e.parent_id
    assert e1.parent_id == e1.e.parent_id

    # AND that these edges' other stuff matches up
    assert e0.rand_idx == e1.rand_idx
    assert e0.cc_num == e1.cc_num
    assert e0.parent_id == e1.parent_id


def test_decouple_all_negative_node_cc_dont_decouple():
    # FASTG and DOT files are unique in that they (1) have node orientations,
    # but (2) are "explicit" -- they typically have both copies of a node
    # given. We (currently) allow such graphs to not be symmetric.
    #
    # This means that this FASTG file, which ONLY includes negative nodes,
    # is allowed.
    #
    # However! There was previously a silly bug here where we would try to
    # decouple this graph's only component, and then crash when we'd try to
    # figure out the starting node to set as + for the BFS. Since none of the
    # nodes in the component are +, we would be calling get_max_degree_node()
    # on an empty list of node IDs.
    #
    # ... So, the solution to this is just detecting this case and not
    # decoupling this component.
    ag = AssemblyGraph("metagenomescope/tests/input/all-negative.fastg")
    assert len(ag.components) == 1
    assert not ag.components[0].decoupling_done


def test_decouple_asymmetric_cc(caplog):
    # As we saw with all-negative.fastg above, FASTG/DOT files can be
    # asymmetric. This is a strand-tangled component that is also asymmetric:
    #
    #         /--> 3
    # -1 -> -2 -> -3
    #
    # The highest-degree forward node here (really, the ONLY forward node)
    # is 3. So, we'll fix that to be +, and then radiate outward. This will
    # invalidate the edge from -2 -> -3.
    #
    # Also, because this component is asymmetric, decoupling it will trigger
    # a warning. We will check that this warning is logged.
    ag = AssemblyGraph(
        "metagenomescope/tests/input/asymm-strand-tangled.fastg"
    )
    assert (
        "WARNING: Component #1 has asymmetric edge counts"
        in caplog.records[0].msg
    )
    assert len(ag.components) == 1
    cc = ag.components[0]
    assert cc.decoupling_done

    assert nodeids2names(ag, cc.dc_shown_node_ids) == ["-1", "-2", "3"]

    assert edgeids2tuplectr(ag, cc.dc_shown_edge_ids) == {
        ("-1", "-2"): 1,
        ("-2", "3"): 1,
    }

    assert len(cc.dc_inval_edges) == 1
    ie = cc.dc_inval_edges[0]
    assert ie.inval_type == config.INVAL_TGT
    assert ie.ports == ("e", "e")
    assert id2name(ag, ie.rc_node_id) == "3"
    # drawn as from -2 -> 3
    assert edge2tuple(ag, ie) == ("-2", "3")
    # but represents -2 -> -3
    assert edge2tuple(ag, ie.e) == ("-2", "-3")
    assert ie.rand_idx == ie.e.rand_idx
    assert ie.cc_num == ie.e.cc_num
    assert ie.parent_id == ie.e.parent_id


def test_decouple_skips_nonstrandtangled_and_one_node_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    for cc in ag.components:
        assert not cc.decoupling_done


def test_decouple_chr15_full():
    ag = AssemblyGraph("metagenomescope/tests/input/chr15_full.gv")
    assert len(ag.components) == 1
    cc = ag.components[0]
    assert cc.decoupling_done

    # Make sure that decoupling the cc keeps exactly one copy of each node
    on2orient = {}
    for nid in cc.dc_shown_node_ids:
        n = ag.nodeid2obj[nid]
        # ignore right split nodes, so that we only count each basename once
        if n.is_not_split() or n.split == config.SPLIT_LEFT:
            on = name_utils.get_orientationless_name(n.basename)
            assert on not in on2orient, f"{on} shown twice in decoupling"
            on2orient[on] = name_utils.get_orientation(n.basename)

    # equal to the number of nodes in the graph (incl + and - copies),
    # divided by 2
    assert len(on2orient) == 502

    for eid in cc.dc_shown_edge_ids:
        e = ag.edgeid2obj[eid]
        assert e.new_src_id in cc.dc_shown_node_ids
        assert e.new_tgt_id in cc.dc_shown_node_ids

    # there are ten palindromic edges -- which show up in the non-decoupled
    # graph as five palindromic bulges. In the decoupled graph, they look like
    # weird self loops that start from and end at the same port of a node.
    # Incident on nodes 249210759, -637271666, -585460321, -21131660,
    # 296237279 (orientations chosen for decoupling might vary, idk, although
    # probs not)
    palindromic_edges = []
    for e in cc.edges:
        srcname = ag.nodeid2obj[e.new_src_id].basename
        tgtname = ag.nodeid2obj[e.new_tgt_id].basename
        if srcname == name_utils.negate(tgtname):
            palindromic_edges.append(e)
    assert len(palindromic_edges) == 10

    pal_ct = 0
    for ie in cc.dc_inval_edges:
        src_shown = ie.e.new_src_id in cc.dc_shown_node_ids
        tgt_shown = ie.e.new_tgt_id in cc.dc_shown_node_ids
        # exactly ONE of {src, tgt} should be shown
        assert src_shown ^ tgt_shown
        src = ag.nodeid2obj[ie.e.new_src_id]
        tgt = ag.nodeid2obj[ie.e.new_tgt_id]
        rc_obj = ag.nodeid2obj[ie.rc_node_id]
        if src_shown:
            assert ie.inval_type == config.INVAL_TGT
            missing = tgt
        else:
            assert ie.inval_type == config.INVAL_SRC
            missing = src
        assert ie.rc_node_id in cc.dc_shown_node_ids
        assert rc_obj.basename == name_utils.negate(missing.basename)

        # find and check palindromic edges X -> -X (or -X -> X, whatever)
        # that have been transformed into self-loops in the decoupling
        if name_utils.negate(src.basename) == tgt.basename:
            if src == missing:
                assert ie.ports == ("w", "w")
            else:
                assert ie.ports == ("e", "e")
            pal_ct += 1
    assert pal_ct == 10
