import pytest
from metagenomescope.errors import WeirdError
from metagenomescope.graph import AssemblyGraph


def _get_user_edge_ids(cc):
    eids = set()
    for e in cc.edges:
        if not e.is_fake:
            eids.add(e.get_userspecified_id())
    return eids


def _get_node_basenames(cc):
    # using a set takes care of split nodes nicely
    bns = set()
    for n in cc.nodes:
        bns.add(n.basename)
    return bns


def test_flye_yeast_nr_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")

    # make sure these exact ccs are reported as the nonredundant ones
    assert ag.get_nr_cc_nums() == {1, 2, 5, 6, 7, 9}

    # ... and that they correspond to the actual components we expect
    assert len(ag.get_cc_by_num(1).nodes) == 39
    assert len(ag.get_cc_by_num(2).nodes) == 10
    assert len(ag.get_cc_by_num(5).nodes) == 2
    assert len(ag.get_cc_by_num(6).nodes) == 2
    assert len(ag.get_cc_by_num(7).nodes) == 1
    assert len(ag.get_cc_by_num(9).nodes) == 1

    assert _get_user_edge_ids(ag.get_cc_by_num(5)) == {"24"}
    assert _get_user_edge_ids(ag.get_cc_by_num(6)) == {"39"}
    assert _get_user_edge_ids(ag.get_cc_by_num(7)) == {"2"}
    assert _get_user_edge_ids(ag.get_cc_by_num(9)) == {"21"}


def test_sample1_nr_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    assert ag.get_nr_cc_nums() == {1, 3}
    assert _get_node_basenames(ag.get_cc_by_num(1)) == {
        "1",
        "2",
        "3",
        "-4",
        "5",
    }
    assert _get_node_basenames(ag.get_cc_by_num(3)) == {"6"}


def test_gml_nr_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/aug1_subgraph.gml")
    with pytest.raises(WeirdError) as ei:
        ag.get_nr_cc_nums()
    assert str(ei.value) == (
        "Nonredundant component information not set. Either you "
        "called this too early OR this graph does not have "
        "reverse-complementary versions of things."
    )


def test_flye_yeast_nr_ccs_extra_edge():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/flye_yeast_extra_edge_in_twin.gv"
    )
    assert ag.get_nr_cc_nums() == {1, 2, 3, 5, 6, 7, 9}


def test_lja_simple_nr_ccs():
    ag = AssemblyGraph("metagenomescope/tests/input/lja-two-rc-ccs.gv")
    assert ag.get_nr_cc_nums() == {1}
    assert _get_node_basenames(ag.get_cc_by_num(1)) == {"123", "456"}


def test_lja_simple_nr_ccs_noedgeids():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/lja-two-rc-ccs-noedgeids.gv"
    )
    assert ag.get_nr_cc_nums() == {1}
    assert _get_node_basenames(ag.get_cc_by_num(1)) == {"123", "456"}


def test_lja_simple_nr_ccs_extra_edge():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/lja-two-rc-ccs-plus-extra-edge.gv"
    )
    assert ag.get_nr_cc_nums() == {1, 2}


def test_flye_bubble_chain_fake_edges_dont_crash_redundant_cc_detection():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_flye.gv")
    assert ag.get_nr_cc_nums() == {1, 2}
