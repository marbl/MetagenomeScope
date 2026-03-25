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
import math
import pytest
import pygraphviz
from metagenomescope.layout import layout_utils as lu
from metagenomescope.errors import WeirdError


def test_get_control_points():
    # Load a completed layout, so that we can test that the control points look
    # exactly the same
    # (you can generate this kind of file by using dot -Txdot [graph.gv])
    cg = pygraphviz.AGraph("metagenomescope/tests/input/lja-two-rc-ccs.xdot")
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


def test_get_control_points_lost_edge(caplog):
    """Tests that, edges with no set control points lead to [].

    See https://github.com/marbl/MetagenomeScope/issues/394.

    Using caplog per https://stackoverflow.com/a/75420303.

    Note about ""s
    --------------
    I wanted to also test what happens if "pos" is not in .attr entirely
    (since using "" as the default seems to me like a strange decision, and
    the type of decision that PyGraphviz might walk back in the future).
    The current code in get_control_points() allows for this case!

    However, it is really hard to *test* this. This is because
    PyGraphviz.ItemAttribute.__delitem__ ensures that ""s are the defaults.
    It seems like we can't even do "del pygraphviz.ItemAttribute.__delitem__"
    to remove that -- we would need additional wizardry like rewriting it with
    a custom method, at which point maybe testing this is not worth the effort.
    """
    cg = pygraphviz.AGraph("metagenomescope/tests/input/lja-two-rc-ccs.xdot")
    # mimic Graphviz "losing" an edge -- the only case i've seen so far where a
    # standard mgsc graph edge gets lost takes 10 minutes to lay out, plus if
    # we encode such a test case here we run the risk of Graphviz fixing this
    # behavior later on and breaking this test. so let's do it ourselves.
    #
    # pygraphviz uses "" as a default for these attributes --
    # https://github.com/pygraphviz/pygraphviz/blob/db16436152047ac03f9a2cc213741021d3b4fd75/pygraphviz/agraph.py#L1970-L1980
    cg.edges()[0].attr["pos"] = ""
    assert lu.get_control_points(cg.edges()[0]) == []
    assert "no coords from Graphviz!" in caplog.text


def test_extract_control_points_basic():
    assert lu._extract_control_points("123,456 789,10112") == [
        123,
        456,
        789,
        10112,
    ]
    assert lu._extract_control_points("1.2,3.4") == [1.2, 3.4]
    assert lu._extract_control_points("1.2,3.4") == [1.2, 3.4]


def test_extract_control_points_odd_ct():
    with pytest.raises(ValueError) as ei:
        lu._extract_control_points("1.2")
    assert str(ei.value) == 'Odd number of GV edge control points: "1.2"'

    with pytest.raises(ValueError) as ei:
        lu._extract_control_points("1.2,3.4 5.6")
    assert (
        str(ei.value) == 'Odd number of GV edge control points: "1.2,3.4 5.6"'
    )


def test_extract_control_points_startp_endp():
    # just start
    assert lu._extract_control_points("s,123,456 789,10112") == [789, 10112]
    # just end
    assert lu._extract_control_points("e,123,456 7,10112") == [7, 10112]
    # start & end
    assert lu._extract_control_points("s,123,400 e,123,456 7,1") == [7, 1]


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


def test_euclidean_distance():
    # just checking that my boy Euclid didn't mess up
    assert lu.euclidean_distance((1, 5), (9, 30)) == math.sqrt(689)
    assert lu.euclidean_distance((1, 2), (3, 4)) == math.sqrt(8)
    assert lu.euclidean_distance((1, 5), (1, 5)) == 0
    assert lu.euclidean_distance((1, 5), (1, 6)) == 1
    assert lu.euclidean_distance((-1, -5), (-1, -6)) == 1
    # apparently i included this in the js tests from like 2020 so sure
    # https://github.com/marbl/MetagenomeScope/blob/dc79e93b1ef01abef66518eb2f55c355d1e273b8/metagenomescope/tests/js_tests/test-utils.js
    # i miss those days... maybe...
    assert lu.euclidean_distance((0, 0), (-12345, 10000000)) == pytest.approx(
        10000007.619948346
    )


def test_point_to_line_distance_basic():
    # https://github.com/marbl/MetagenomeScope/blob/dc79e93b1ef01abef66518eb2f55c355d1e273b8/metagenomescope/tests/js_tests/test-utils.js
    # example datasets from
    # https://www.intmath.com/plane-analytic-geometry/perpendicular-distance-point-line.php
    assert lu.point_to_line_distance(
        (5, 6), (0, -4 / 3), (2, 0)
    ) == pytest.approx(12 / math.sqrt(13))
    assert lu.point_to_line_distance(
        (-3, 7), (0, 2), (-5 / 3, 0)
    ) == pytest.approx(-43 / math.sqrt(61))


def test_point_to_line_distance_zerozero_point():
    # based on first example from
    # https://www.intmath.com/plane-analytic-geometry/perpendicular-distance-point-line.php
    assert lu.point_to_line_distance(
        (0, 0), (0, -4 / 3), (2, 0)
    ) == pytest.approx(4 / math.sqrt(13))


def test_point_to_line_distance_horizontal_line():
    # line is at y = 1; the point (2, 0) is below the line
    assert lu.point_to_line_distance((2, 0), (1, 1), (8, 1)) == -1
    # the point (2, 2) is now above the line and equally far from it but in the
    # opposite direction
    assert lu.point_to_line_distance((2, 2), (1, 1), (8, 1)) == 1


def test_point_to_line_distance_vertical_line():
    # line is at x = -1; the point (1.5, 0) is to the right of the line
    assert lu.point_to_line_distance((1.5, 0), (-1, -1), (-1, 6)) == -2.5
    # the point at (-1.5, 0) is to the left of the line
    assert lu.point_to_line_distance((-1.5, 0), (-1, -1), (-1, 6)) == 0.5


def test_point_to_line_distance_zero_distance_line():
    with pytest.raises(WeirdError) as ei:
        lu.point_to_line_distance((1, 2), (3, 4), (3, 4))
    assert str(ei.value) == (
        "d((1, 2), line): distance from (3, 4) to (3, 4) on line is zero?"
    )


def test_dot_to_cyjs_control_points_loop_flattened():
    assert lu.dot_to_cyjs_control_points(
        (1, 2), (1, 2), [3, 2, 7, 2, 9, 2], 200, None, None, 0, 0
    ) == (True, None, None)


def test_dot_to_cyjs_control_points_empty_control_points_flattened():
    # lost edge #394 thing
    assert lu.dot_to_cyjs_control_points(
        (1, 2), (3, 4), [], 200, None, None, 0, 0
    ) == (True, None, None)


def test_dot_to_cyjs_control_points_straightline_flattened():
    # straight horizontal line
    assert lu.dot_to_cyjs_control_points(
        (1, 198), (10, 198), [3, 2, 7, 2, 9, 2], 200, None, None, 0, 0
    ) == (True, None, None)

    # straight vertical line
    assert lu.dot_to_cyjs_control_points(
        (1, 180), (1, 199), [1, 5, 1, 10], 200, None, None, 0, 0
    ) == (True, None, None)


def test_dot_to_cyjs_control_points_basic():
    # (7, 50) (aka (7, 150) due to flipheight = 200) is far enough from
    # the horizontal line (relative to layout_config.CTRL_PT_DIST_EPSILON)
    # that it causes these control points to no longer be representable as
    # a simple straight line. Therefore, we should actually get Cytoscape.js-
    # compatible control points.
    assert lu.dot_to_cyjs_control_points(
        (1, 198), (10, 198), [3, 2, 7, 50, 9, 2], 200, None, None, 0, 0
    ) == (False, "0.0000 -48.0000 0.0000", "0.2222 0.6667 0.8889")


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
