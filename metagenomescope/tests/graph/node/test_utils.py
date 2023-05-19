import pytest
from metagenomescope.graph.node import get_node_name
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
    assert str(ei.value) == (
        f'"split" is {SPLIT_SEP}, but it should be one of {{None, '
        f'"{SPLIT_LEFT}", "{SPLIT_RIGHT}"}}.'
    )
