import pytest
from metagenomescope import config
from metagenomescope.graph import PatternStats
from metagenomescope.errors import WeirdError


def test_add():
    ps = PatternStats(
        num_bubbles=1,
        num_chains=2,
        num_cyclicchains=3,
        num_frayedropes=4,
        num_bipartites=3,
    )
    ps += PatternStats(num_bubbles=50, num_cyclicchains=2)
    assert ps.num_bubbles == 51
    assert ps.num_chains == 2
    assert ps.num_cyclicchains == 5
    assert ps.num_frayedropes == 4
    assert ps.num_bipartites == 3


def test_repr():
    ps = PatternStats(
        num_bubbles=1,
        num_chains=2,
        num_cyclicchains=3,
        num_frayedropes=4,
        num_bipartites=5,
    )
    assert repr(ps) == (
        "PatternStats(1 bubble(s), 2 chain(s), 3 cyclic chain(s), 4 frayed "
        "rope(s), 5 bipartite(s))"
    )


def test_sum():
    ps = PatternStats()
    assert ps.sum() == 0

    ps = PatternStats(num_frayedropes=1)
    assert ps.sum() == 1

    ps = PatternStats(
        num_bubbles=1, num_chains=2, num_cyclicchains=3, num_frayedropes=4
    )
    assert ps.sum() == 10
    ps += PatternStats(num_bipartites=1)
    assert ps.sum() == 11


def test_update_good():
    ps = PatternStats()
    assert ps.num_bubbles == 0
    assert ps.num_chains == 0
    assert ps.num_cyclicchains == 0
    assert ps.num_frayedropes == 0
    assert ps.num_bipartites == 0

    ps.update(config.PT_BUBBLE)
    assert ps.num_bubbles == 1
    assert ps.num_chains == 0
    assert ps.num_cyclicchains == 0
    assert ps.num_frayedropes == 0
    assert ps.num_bipartites == 0

    ps.update(config.PT_FRAYEDROPE)
    assert ps.num_bubbles == 1
    assert ps.num_chains == 0
    assert ps.num_cyclicchains == 0
    assert ps.num_frayedropes == 1
    assert ps.num_bipartites == 0

    ps.update(config.PT_FRAYEDROPE)
    assert ps.num_bubbles == 1
    assert ps.num_chains == 0
    assert ps.num_cyclicchains == 0
    assert ps.num_frayedropes == 2
    assert ps.num_bipartites == 0

    ps.update(config.PT_BIPARTITE)
    assert ps.num_bubbles == 1
    assert ps.num_chains == 0
    assert ps.num_cyclicchains == 0
    assert ps.num_frayedropes == 2
    assert ps.num_bipartites == 1


def test_update_bad_type():
    ps = PatternStats()
    with pytest.raises(WeirdError) as ei:
        ps.update("impostor")
    assert str(ei.value) == "Unrecognized pattern type: impostor"
