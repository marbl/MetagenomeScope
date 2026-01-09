import pytest
from metagenomescope.errors import WeirdError
from metagenomescope.graph import DrawResults


def test_init_empty():
    dr = DrawResults()
    assert dr.eles == []
    assert dr.nodect == 0
    assert dr.edgect == 0
    assert dr.pattct == 0
    assert dr.nodeids is None
    assert dr.edgeids is None


def test_init_inconsistent_lengths():
    with pytest.raises(WeirdError) as ei:
        DrawResults(
            [
                {"data": {"id": "asdf"}},
                {"data": {"id": "butt"}},
                {"data": {"source": "asdf", "target": "butt"}},
            ],
            nodect=3,
            edgect=1,
        )
    assert str(ei.value) == (
        "3 ele(s), but (3 node(s) + 1 edge(s) + 0 patt(s)) = 4?"
    )


def test_add():
    dr = DrawResults()
    dr += DrawResults(
        [
            {"data": {"id": "asdf"}},
            {"data": {"id": "butt"}},
            {"data": {"source": "asdf", "target": "butt"}},
        ],
        nodect=2,
        edgect=1,
    )
    assert dr.eles == [
        {"data": {"id": "asdf"}},
        {"data": {"id": "butt"}},
        {"data": {"source": "asdf", "target": "butt"}},
    ]
    assert dr.nodect == 2
    assert dr.edgect == 1
    assert dr.pattct == 0
    assert dr.nodeids is None
    assert dr.edgeids is None


def test_repr():
    dr = DrawResults(
        [
            {"data": {"id": "asdf"}},
            {"data": {"id": "butt"}},
            {"data": {"source": "asdf", "target": "butt"}},
        ],
        nodect=2,
        edgect=1,
    )
    assert repr(dr) == (
        "DrawResults(3 ele(s) [2 node(s) + 1 edge(s) + 0 patt(s)], "
        "ids not given)"
    )
