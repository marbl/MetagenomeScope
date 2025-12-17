from metagenomescope.graph import AssemblyGraph


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
