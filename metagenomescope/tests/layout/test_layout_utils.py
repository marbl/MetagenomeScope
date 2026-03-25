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
import pygraphviz
from metagenomescope.layout import layout_utils as lu


def test_get_control_points():
    # Load a completed layout, so that we can test that the control points look
    # exactly the same
    # (you can generate this kind of file by using dot -Txdot [graph.gv])
    cg = pygraphviz.AGraph("metagenomescope/tests/input/lja-two-rc-ccs.xdot")
    cg.layout(prog="dot")
    src2e = {}
    for e in cg.edges():
        src2e[e[0]] = e

    assert len(src2e) == 2
    assert sorted(src2e.keys()) == ["-456", "123"]

    # skip first points beginning with "e," or "s,"
    assert lu.get_control_points(src2e["123"]) == [
        24.466,
        88.091,
        23.763,
        82.488,
        23.097,
        76.243,
        22.75,
        70.5,
        22.307,
        63.18,
        22.307,
        61.32,
        22.75,
        54,
        22.875,
        51.936,
        23.041,
        49.807,
        23.235,
        47.667,
    ]
    assert lu.get_control_points(src2e["-456"]) == [
        160,
        88.41,
        160,
        76.758,
        160,
        61.047,
        160,
        47.519,
    ]


def test_shift_control_points_good():
    shifted = lu.shift_control_points([1, 2, 3, 4, 5, 6, 7, 8], 100, 1)
    assert shifted == [101, 3, 103, 5, 105, 7, 107, 9]

    whatever = [-1, -2, -2, -3, -9, 10, 100, 1000, 6, 0]
    assert lu.shift_control_points(whatever, 0, 0) == whatever

    assert lu.shift_control_points([10, 10], 5.3, -2) == [15.3, 8]


def test_shift_control_points_odd():
    # If there are an odd number of coordinates, something is very wrong, so
    # an error should be raised.
    with pytest.raises(ValueError):
        lu.shift_control_points([1], 1, 2)

    with pytest.raises(ValueError):
        lu.shift_control_points([1, 2, 3], 10, 100)


def test_getxy():
    assert lu.getxy("5,-2") == (5, -2)
    assert lu.getxy("123.456,789.012") == (123.456, 789.012)
    # I'm pretty sure GraphViz doesn't include leading/trailing whitespace in
    # these position attributes, but even if this would change we should still
    # be able to handle that
    assert lu.getxy(" 123.456 , 789.012  ") == (123.456, 789.012)
    assert lu.getxy(" -123.456 , 789.012  ") == (-123.456, 789.012)
    assert lu.getxy(" 123.456 , -789.012  ") == (123.456, -789.012)
    assert lu.getxy(" -123.456 , -789.012  ") == (-123.456, -789.012)

    # Errors when not exactly one ","
    with pytest.raises(ValueError):
        lu.getxy("haha i am going to cause problems")

    with pytest.raises(ValueError):
        lu.getxy("1,2,3")

    with pytest.raises(ValueError):
        lu.getxy("1,2,3,4")

    # Error when values aren't valid representations of numbers
    with pytest.raises(ValueError):
        lu.getxy("a,b")

    with pytest.raises(ValueError):
        lu.getxy("one, two")
