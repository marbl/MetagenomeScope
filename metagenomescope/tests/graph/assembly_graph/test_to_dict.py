from metagenomescope.graph import AssemblyGraph


def test_to_dict_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    data = ag.to_dict()
    assert type(data) == dict
