from metagenomescope.graph_objects import AssemblyGraph


def test_to_dict_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    ag.process()

    data = ag.to_dict()
    assert type(data) == dict
