from metagenomescope.graph import PatternStats


def test_add():
    ps = PatternStats(
        num_bubbles=1, num_chains=2, num_cyclicchains=3, num_frayedropes=4
    )
    ps += PatternStats(num_bubbles=50, num_cyclicchains=2)
    assert ps.num_bubbles == 51
    assert ps.num_chains == 2
    assert ps.num_cyclicchains == 5
    assert ps.num_frayedropes == 4


def test_repr():
    ps = PatternStats(
        num_bubbles=1, num_chains=2, num_cyclicchains=3, num_frayedropes=4
    )
    assert repr(ps) == (
        "PatternStats(1 bubble(s), 2 chain(s), 3 cyclic chain(s), 4 frayed "
        "rope(s))"
    )
