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
