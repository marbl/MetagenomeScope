from metagenomescope.graph import AssemblyGraph


def _agg(out):
    name2covlen = {}
    assert len(out[0]) == len(out[1])
    assert len(out[1]) == len(out[2])
    for name, cov, length in zip(*out[:3]):
        assert name not in name2covlen
        name2covlen[name] = (cov, length)
    return name2covlen


def test_sample1():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    out = ag.to_covlen_ele_scatter()
    assert _agg(out) == {"3": (4 / 21, 21), "-3": (4 / 21, 21)}
    assert out[-1] is not None
