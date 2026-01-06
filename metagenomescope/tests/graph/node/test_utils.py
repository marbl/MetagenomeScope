import pytest
from metagenomescope.graph.node import get_node_name, get_opposite_split
from metagenomescope.config import SPLIT_SEP, SPLIT_LEFT, SPLIT_RIGHT
from metagenomescope.errors import WeirdError


def test_get_node_name():
    assert get_node_name("1234", None) == "1234"
    assert get_node_name("1234", SPLIT_LEFT) == f"1234{SPLIT_SEP}{SPLIT_LEFT}"
    assert get_node_name("1234", SPLIT_RIGHT) == (
        f"1234{SPLIT_SEP}{SPLIT_RIGHT}"
    )
    with pytest.raises(WeirdError) as ei:
        get_node_name("1234", SPLIT_SEP)
    assert str(ei.value) == f"Invalid split type for node 1234: {SPLIT_SEP}"


def test_get_opposite_split():
    assert get_opposite_split(SPLIT_LEFT) == SPLIT_RIGHT
    assert get_opposite_split(SPLIT_RIGHT) == SPLIT_LEFT

    with pytest.raises(WeirdError) as ei:
        get_opposite_split(None)
    assert str(ei.value) == (
        f"split is None, but it should be {SPLIT_LEFT} or {SPLIT_RIGHT}?"
    )

    with pytest.raises(WeirdError) as ei:
        get_opposite_split("floobity")
    assert str(ei.value) == (
        f"split is floobity, but it should be {SPLIT_LEFT} or {SPLIT_RIGHT}?"
    )
