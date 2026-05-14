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
from metagenomescope import gfa_utils as gu
from metagenomescope.errors import GraphParsingError


def test_check_enough_line_parts():
    gu.check_enough_line_parts("asdf\tdef", ["asdf", "def"], 0)
    gu.check_enough_line_parts("asdf\tdef", ["asdf", "def"], 1)
    gu.check_enough_line_parts("asdf\tdef", ["asdf", "def"], 2)

    with pytest.raises(GraphParsingError) as ei:
        gu.check_enough_line_parts("asdf\tdef", ["asdf", "def"], 3)
    assert str(ei.value) == 'Less than 3 parts: GFA line "asdf\tdef"'


def test_get_tag_dict_simple():
    assert gu.get_tag_dict([]) == {}
    assert gu.get_tag_dict(["LN:i:12345"]) == {"ln:i": "12345"}
    assert gu.get_tag_dict(
        ["LN:i:12345", "KC:i:333", "RC:i:2", "DP:f:9.23145"]
    ) == {"ln:i": "12345", "kc:i": "333", "rc:i": "2", "dp:f": "9.23145"}


def test_get_tag_dict_not_enough_colons():
    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["LN:i12345"])
    assert str(ei.value) == 'Found a GFA tag with < 2 colons: "LN:i12345"'

    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["LNi12345"])
    assert str(ei.value) == 'Found a GFA tag with < 2 colons: "LNi12345"'

    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict([""])
    assert str(ei.value) == 'Found a GFA tag with < 2 colons: ""'


def test_get_tag_dict_zero_length_suffix():
    # (a zero-length prefix is impossible atm lol, but we can at least test
    # zero-length values)
    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["LN:i:"])
    assert str(ei.value) == 'Zero-length tag prefix or value: "LN:i:"'

    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["::"])
    assert str(ei.value) == 'Zero-length tag prefix or value: "::"'


def test_get_tag_dict_duplicate_tag_prefix():
    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["LN:i:5", "ln:i:99"])
    assert str(ei.value) == 'Duplicate GFA tag prefix: "ln:i"'

    with pytest.raises(GraphParsingError) as ei:
        gu.get_tag_dict(["LN:i:5", "dp:f:123", "ln:i:99"])
    assert str(ei.value) == 'Duplicate GFA tag prefix: "ln:i"'


def test_is_dovetail_simple():
    # Based on the GFA 2 specification's rules:
    # https://gfa-spec.github.io/GFA-spec/GFA2.html#edge

    # Same orientation: beg1 = 0 and end2 = y$
    #
    # Looks like
    #         |  |
    # 1. <--------
    # 2.      <--------
    assert gu.is_dovetail("-", "-", "0", "5", "7", "9$")

    # Same orientation: beg2 = 0 and end1 = x$
    #
    # Looks like
    #         |  |
    # 1. -------->
    # 2.      -------->
    assert gu.is_dovetail("+", "+", "1", "3$", "0", "4")

    # Opposite orientations: beg1 = 0 and beg2 = 0
    #
    # Looks like
    #         |  |
    # 1. <--------
    # 2.      -------->
    assert gu.is_dovetail("-", "+", "0", "3", "0", "4")

    # Opposite orientations: end1 = x$ and end2 = y$
    #
    # Looks like
    #         |  |
    # 1. -------->
    # 2.      <--------
    assert gu.is_dovetail("+", "-", "2", "3$", "2", "4$")


def test_is_dovetail_weird_stuff():
    # Looks like
    #         |  |
    # 1.      -------->
    # 2. -------->
    #
    # I mean I don't know why you would write out the edge
    # like this but per the GFA 2 rules it technically counts as a dovetail?
    # Maybe we should prevent this. For now let's allow it and test that it is
    # allowed, so that if/when we change this behavior we can loudly know to
    # fix this
    assert gu.is_dovetail("+", "+", "0", "5", "2", "9$")
