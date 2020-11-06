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
from metagenomescope import layout_utils


def test_shift_control_points_good():
    shifted = layout_utils.shift_control_points(
        [1, 2, 3, 4, 5, 6, 7, 8], 100, 1
    )
    assert shifted == [101, 3, 103, 5, 105, 7, 107, 9]

    whatever = [-1, -2, -2, -3, -9, 10, 100, 1000, 6, 0]
    assert layout_utils.shift_control_points(whatever, 0, 0) == whatever

    assert layout_utils.shift_control_points([10, 10], 5.3, -2) == [15.3, 8]

def test_shift_control_points_odd():
    # If there are an odd number of coordinates, something is very wrong, so
    # an error should be raised.
    with pytest.raises(ValueError):
        layout_utils.shift_control_points([1], 1, 2)

    with pytest.raises(ValueError):
        layout_utils.shift_control_points([1, 2, 3], 10, 100)
