from collections import Counter
from metagenomescope import config
from metagenomescope.graph import AssemblyGraph

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


def test_decouple_components():
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
