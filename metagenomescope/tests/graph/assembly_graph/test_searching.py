import pytest
from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import UIError


def test_get_nodename2ccnum_singlenode():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # This graph has two twin components, so which is size rank 1 and which is
    # size rank 2 is arbitrary (I think). Let's be generous and allow either to
    # pass the test.
    d = ag.get_nodename2ccnum("3")
    assert d == {"3": 1} or d == {"3": 2}


def test_get_nodename2ccnum_multinode():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    d = ag.get_nodename2ccnum("1, 35, 48")
    assert d == {"1": 1, "35": 1, "48": 2}


def test_get_nodename2ccnum_multinode_and_input_duplicates():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    d = ag.get_nodename2ccnum("1, 35, 48,,,1,35,,48")
    assert d == {"1": 1, "35": 1, "48": 2}


def test_get_nodename2ccnum_missing_node():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    with pytest.raises(UIError) as ei:
        ag.get_nodename2ccnum("1, 35, 48,,,1,35,,48,poop")
    assert str(ei.value) == 'Can\'t find a node with name "poop" in the graph.'


def test_get_nodename2ccnum_missing_multiple_nodes():
    ag = AssemblyGraph("metagenomescope/tests/input/flye_yeast.gv")
    with pytest.raises(UIError) as ei:
        ag.get_nodename2ccnum("1, 35, 48,,,1,35,,48,poop,help,what")
    # the list of bad node names is sorted so we know it should look like this
    assert str(ei.value) == (
        'Can\'t find nodes with names "help", "poop", "what" in the graph.'
    )


def test_get_nodename2ccnum_empty():
    # this error is actually caused by ui_utils.get_node_names(), which we are
    # already testing separately... this is just a quick test that tries to
    # verify that this work is being properly delegated to that function
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(UIError) as ei:
        ag.get_nodename2ccnum(",,,")
    assert str(ei.value) == "No node name(s) specified."


def test_get_nodename2ccnum_splitnodes_ok():
    # see test_bubble_chain_identification() for a nice diagram abt this graph
    # basically it has two split nodes: 4-L ==> 4-R
    ag = AssemblyGraph("metagenomescope/tests/input/bubble_chain_test.gml")
    assert ag.get_nodename2ccnum("4") == {"4-L": 1, "4-R": 1}
    assert ag.get_nodename2ccnum("4-L") == {"4-L": 1}
    assert ag.get_nodename2ccnum("4-R") == {"4-R": 1}
    assert ag.get_nodename2ccnum("4-L, 4-R") == {"4-L": 1, "4-R": 1}
    assert ag.get_nodename2ccnum("4-L, 4-R, 4") == {"4-L": 1, "4-R": 1}
    assert ag.get_nodename2ccnum("4-L, 4") == {"4-L": 1, "4-R": 1}
    assert ag.get_nodename2ccnum("4-R, 4") == {"4-L": 1, "4-R": 1}
