import random
import pytest
from collections import Counter
from metagenomescope import color_utils
from metagenomescope.errors import WeirdError


def test_get_rand_idx_list_basic():
    random.seed(333)
    assert color_utils.get_rand_idx_list(5) == [3, 0, 1, 2, 4]
    assert color_utils.get_rand_idx_list(2) == [0, 1]
    assert color_utils.get_rand_idx_list(1) == [0]


def test_get_rand_idx_list_zero():
    with pytest.raises(WeirdError):
        color_utils.get_rand_idx_list(0)


def test_get_rand_idx_basic():
    random.seed(333)
    gen = color_utils.get_rand_idx(5)

    indices = []
    count = 0
    while count < 5:
        indices.append(next(gen))
        count += 1

    # Since get_rand_idx() uses list.pop() (which takes from the end),
    # this will be backwards from the [3, 0, 1, 2, 4] output in
    # test_get_rand_idx_list_basic() above.
    assert indices == [4, 2, 1, 0, 3]


def test_get_rand_idx_cycles():
    random.seed(12345)
    gen = color_utils.get_rand_idx(7)

    # Select 35 random indices. Because this is evenly divisible by n = 7,
    # we should see each index the same amount of times.
    indices = []
    curr_cycle = []
    count = 0
    while count < 35:
        if count % 7 == 0:
            curr_cycle = []
        i = next(gen)
        assert i not in curr_cycle
        curr_cycle.append(i)
        indices.append(i)
        count += 1

    ctr = Counter(indices)
    for i in (0, 1, 2, 3, 4, 5, 6):
        assert ctr[i] == 5


def test_selectively_interpolate_hsl_bad_lrange():
    with pytest.raises(WeirdError):
        color_utils.selectively_interpolate_hsl([True, True], Lmin=30, Lmax=30)
    with pytest.raises(WeirdError):
        color_utils.selectively_interpolate_hsl([True, True], Lmin=30, Lmax=20)


def test_selectively_interpolate_hsl():
    c = color_utils.selectively_interpolate_hsl(
        [True, True], Lmin=0, Lmax=100, H=255, S=29
    )
    assert c == ["hsl(255,29%,100.0%)", "hsl(255,29%,0.0%)"]


def test_selectively_interpolate_hsl_dark_to_light():
    c = color_utils.selectively_interpolate_hsl(
        [True, True], Lmin=0, Lmax=100, H=255, S=29, light_to_dark=False
    )
    assert c == ["hsl(255,29%,0.0%)", "hsl(255,29%,100.0%)"]


def test_selectively_interpolate_hsl_omit():
    c = color_utils.selectively_interpolate_hsl(
        [True, False], Lmin=0, Lmax=100, H=255, S=29
    )
    assert c == ["hsl(255,29%,100.0%)", ""]

    c = color_utils.selectively_interpolate_hsl(
        [False, True], Lmin=0, Lmax=100, H=255, S=29
    )
    assert c == ["", "hsl(255,29%,0.0%)"]

    c = color_utils.selectively_interpolate_hsl(
        [False, False], Lmin=0, Lmax=100, H=255, S=29
    )
    assert c == ["", ""]


def test_selectively_interpolate_hsl_bigger_range():
    c = color_utils.selectively_interpolate_hsl(
        [False, True, True, False, True, True], Lmin=20, Lmax=50, H=30, S=60.3
    )
    assert c == [
        "",
        "hsl(30,60.3%,44.0%)",
        "hsl(30,60.3%,38.0%)",
        "",
        "hsl(30,60.3%,26.0%)",
        "hsl(30,60.3%,20.0%)",
    ]
