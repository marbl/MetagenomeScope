import pytest
from metagenomescope.errors import WeirdError
from metagenomescope.graph import AssemblyGraph
from metagenomescope.ui_config import (
    CHART_NODES as N,
    CHART_EDGES as E,
    CHART_DOUBLE as D,
    CHART_SINGLE as S,
)


def test_to_treemap_one_cc_fails():
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_test.gml")
    with pytest.raises(WeirdError) as ei:
        ag.get_cc_ele_cts(N, nr_type=D)
    assert str(ei.value) == "Graph has only a single component"
    with pytest.raises(WeirdError) as ei:
        ag.get_cc_ele_cts(N, nr_type=S)
    assert str(ei.value) == "Graph has only a single component"


def test_get_cc_ele_cts_sample1_gfa():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    assert ag.get_cc_ele_cts(N, nr_type=D) == [5, 5, 1, 1]
    assert ag.get_cc_ele_cts(E, nr_type=D) == [4, 4, 0, 0]
    assert ag.get_cc_ele_cts(N, nr_type=S) == [5, 1]
    assert ag.get_cc_ele_cts(E, nr_type=S) == [4, 0]


def test_get_cc_ele_cts_decoupled():
    ag = AssemblyGraph(
        "metagenomescope/tests/input/strand-tangled-with-other-ccs.gfa"
    )
    assert ag.get_cc_ele_cts(N, nr_type=D) == [6, 1, 1, 1, 1]
    assert ag.get_cc_ele_cts(E, nr_type=D) == [6, 1, 1, 0, 0]
    assert ag.get_cc_ele_cts(N, nr_type=S) == [3, 1, 1]
    assert ag.get_cc_ele_cts(E, nr_type=S) == [3, 1, 0]


def test_get_cc_ele_cts_loop_gfa():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    assert ag.get_cc_ele_cts(N, nr_type=D) == [2, 2, 1, 1, 1, 1]
    assert ag.get_cc_ele_cts(E, nr_type=D) == [1, 1, 1, 1, 1, 1]
    assert ag.get_cc_ele_cts(N, nr_type=S) == [1, 1, 1, 1]
    assert ag.get_cc_ele_cts(E, nr_type=S) == [1, 1, 1, 1]


def test_get_cc_ele_cts_asymm_decoupled():
    # two components, which look (before decoupling) like
    # -1 -> -2 -> -3
    #         \->  3
    # 4
    ag = AssemblyGraph(
        "metagenomescope/tests/input/asymm-strand-tangled-multicc.fastg"
    )
    assert ag.get_cc_ele_cts(N, nr_type=D) == [4, 1]
    assert ag.get_cc_ele_cts(E, nr_type=D) == [3, 0]
    assert ag.get_cc_ele_cts(N, nr_type=S) == [3, 1]
    assert ag.get_cc_ele_cts(E, nr_type=S) == [3, 0]


def test_get_cc_ele_cts_lja_dot():
    ag = AssemblyGraph("metagenomescope/tests/input/lja-two-rc-ccs.gv")
    assert ag.get_cc_ele_cts(N, nr_type=D) == [2, 2]
    assert ag.get_cc_ele_cts(E, nr_type=D) == [1, 1]
    assert ag.get_cc_ele_cts(N, nr_type=S) == [2]
    assert ag.get_cc_ele_cts(E, nr_type=S) == [1]
