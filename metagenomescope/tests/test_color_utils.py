import random
import pytest

from metagenomescope import color_utils
from metagenomescope.errors import WeirdError


def test_get_rand_idx_list_basic():
    random.seed(333)
    assert color_utils.get_rand_idx_list(5) == [3, 0, 1, 2, 4]
    assert color_utils.get_rand_idx_list(2) == [0, 1]
    assert color_utils.get_rand_idx_list(1) == [0]


def test_get_rand_idx_list_zero():
    with pytest.raises(WeirdError) as ei:
        color_utils.get_rand_idx_list(0)
