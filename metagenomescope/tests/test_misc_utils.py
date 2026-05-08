# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from metagenomescope import misc_utils as mu
from metagenomescope.errors import WeirdError


def test_verify_single():
    mu.verify_single([1])
    mu.verify_single([None])
    mu.verify_single([10000])

    with pytest.raises(WeirdError) as ei:
        mu.verify_single([1, 2])
    assert str(ei.value) == "[1, 2] contains 2 items, instead of 1"

    with pytest.raises(WeirdError) as ei:
        mu.verify_single([1, 1])
    assert str(ei.value) == "[1, 1] contains 2 items, instead of 1"

    with pytest.raises(WeirdError) as ei:
        mu.verify_single([1, 1, 100])
    assert str(ei.value) == "[1, 1, 100] contains 3 items, instead of 1"


def test_verify_unique():
    mu.verify_unique([1, 2, 3])
    with pytest.raises(WeirdError) as ei:
        mu.verify_unique([1, 2, 3, 2])
    assert str(ei.value) == "Duplicate IDs: [1, 2, 3, 2]"

    with pytest.raises(WeirdError) as ei:
        mu.verify_unique([1, 2, 3, 200, 3, 5], "thingz")
    assert str(ei.value) == "Duplicate thingz: [1, 2, 3, 200, 3, 5]"


def test_verify_subset():
    mu.verify_subset([1, 2, 3], [1, 2, 3])
    mu.verify_subset([1, 2, 3], [1, 2, 3, 4])
    with pytest.raises(WeirdError) as ei:
        mu.verify_subset([1, 2, 3], [1, 2])
    assert str(ei.value) == "[1, 2, 3] is not a subset of [1, 2]"


def test_verify_subset_custom_message():
    mu.verify_subset([1, 2, 3], [1, 2, 3], custom_message="bloobity")
    mu.verify_subset([1, 2, 3], [1, 2, 3, 4], custom_message="scrimblo")
    with pytest.raises(WeirdError) as ei:
        mu.verify_subset([1, 2, 3], [1, 2], custom_message="floompty")
    assert str(ei.value) == "floompty"


def test_get_basename_if_fp():
    assert mu.get_basename_if_fp(None) is None
    assert mu.get_basename_if_fp("abcdef.ghjil") == "abcdef.ghjil"
    assert mu.get_basename_if_fp("/path/to/this/thing/test.txt") == "test.txt"


def test_move_to_start_if_in():
    c = ["abc", "def", "ghi"]
    mu.move_to_start_if_in(c, "def")
    assert c == ["def", "abc", "ghi"]

    mu.move_to_start_if_in(c, "oijadsf")
    assert c == ["def", "abc", "ghi"]


def test_move_to_end_if_in():
    c = ["abc", "def", "ghi"]
    mu.move_to_end_if_in(c, "def")
    assert c == ["abc", "ghi", "def"]

    mu.move_to_end_if_in(c, "oijadsf")
    assert c == ["abc", "ghi", "def"]

    mu.move_to_end_if_in(c, "def")
    assert c == ["abc", "ghi", "def"]


def test_expand2tuples_simple():
    # expand both sides
    assert mu.expand2tuples([1, 2, 3, (4, 5), 6, 7]) == [1, 2, 3, 4, 5, 6, 7]

    # expand both sides of a self loop
    assert mu.expand2tuples([1, 2, 3, (4, 4), 6, 7]) == [1, 2, 3, 4, 4, 6, 7]

    # expand only the left side
    assert mu.expand2tuples([1, 2, 3, (4, 6), 6, 7]) == [1, 2, 3, 4, 6, 7]

    # expand only the right side
    assert mu.expand2tuples([1, 2, 3, (3, 4), 6, 7]) == [1, 2, 3, 4, 6, 7]

    # expand neither side
    assert mu.expand2tuples([1, 2, 3, (3, 6), 6, 7]) == [1, 2, 3, 6, 7]

    # no 2-tuples
    assert mu.expand2tuples([1, 2, 3, 4, 5, 6]) == [1, 2, 3, 4, 5, 6]


def test_expand2tuples_adjacent_2tuples():
    assert mu.expand2tuples([(1, 2), (2, 3), (3, 4)]) == [1, 2, 3, 4]

    assert mu.expand2tuples([(1, 2), 2, (2, 3), (3, 4)]) == [1, 2, 3, 4]

    assert mu.expand2tuples([(1, 2), 2, (2, 5), (3, 4)]) == [1, 2, 5, 3, 4]

    assert mu.expand2tuples([(1, 2), 2, (2, 4), (3, 4)]) == [1, 2, 4, 3, 4]

    assert mu.expand2tuples([(1, 2), 2, (2, 4), (4, 4)]) == [1, 2, 4, 4]

    # from the function docstring
    assert mu.expand2tuples([("a", "b"), ("b", "c"), ("c", "d")]) == [
        "a",
        "b",
        "c",
        "d",
    ]


def test_expand2tuples_justone():
    # one 2-tuple and nothing else
    assert mu.expand2tuples([(1, 2)]) == [1, 2]

    # one normal element and nothing else
    assert mu.expand2tuples([5]) == [5]


def test_expand2tuples_loops():
    # Graph with a self-loop edge "E" from S -> S, and another edge S -> S_2.
    #
    # S --> S_2
    # ^ \
    # | | E
    # +-+
    #
    # The path we are considering is {S} E E E {S_2}.
    # Each traversal of E adds on a single instance of S. It's kind of like
    # reading out a sequence from a de Bruijn graph.
    assert mu.expand2tuples([1, (1, 1), (1, 1), (1, 1), 2]) == [1, 1, 1, 1, 2]

    assert mu.expand2tuples([(1, 1)]) == [1, 1]
    assert mu.expand2tuples([(1, 1), 1]) == [1, 1]
    assert mu.expand2tuples([(1, 1), 2]) == [1, 1, 2]
