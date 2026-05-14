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


def test_store_gfa_id_simple():
    seenid2type = {"asdf": "S", "ghjk": "E"}
    gu.store_gfa_id("qwerty", seenid2type, "S")
    assert seenid2type == {"asdf": "S", "ghjk": "E", "qwerty": "S"}
    gu.store_gfa_id("zzz", seenid2type, "P")
    assert seenid2type == {"asdf": "S", "ghjk": "E", "qwerty": "S", "zzz": "P"}


def test_store_gfa_id_notunique():
    with pytest.raises(GraphParsingError) as ei:
        gu.store_gfa_id("asdf", {"asdf": "S", "ghjk": "E"}, "P")
    assert str(ei.value) == 'ID "asdf" not unique.'


def test_store_gfa_id_segment_with_asterisk_as_id():
    seenid2type = {"asdf": "S", "ghjk": "E"}

    # technically this is allowed in gfa 2 - see comments for store_gfa_id()
    gu.store_gfa_id("*", seenid2type, "S")
    assert seenid2type == {"asdf": "S", "ghjk": "E", "*": "S"}

    # but as soon as we see ANOTHER segment with an ID of "*", then we'll crash
    with pytest.raises(GraphParsingError) as ei:
        gu.store_gfa_id("*", seenid2type, "S")
    assert str(ei.value) == 'ID "*" not unique.'


def test_store_gfa_id_path_with_asterisk_as_id():
    # in theory we could handle this like segments with * IDs (allow the first
    # path with a * ID, then fail when we see another * ID path), but...
    #
    # in GFA 2 a O-line having * as an ID indicates that it has no ID, and
    # I really want to be clear that we don't support that
    seenid2type = {"asdf": "S", "ghjk": "E"}
    with pytest.raises(GraphParsingError) as ei:
        gu.store_gfa_id("*", seenid2type, "P")
    assert str(ei.value) == (
        'P-line with placeholder ID "*" found. We do not support paths '
        "without defined IDs."
    )
    with pytest.raises(GraphParsingError) as ei:
        gu.store_gfa_id("*", seenid2type, "O")
    assert str(ei.value) == (
        'O-line with placeholder ID "*" found. We do not support paths '
        "without defined IDs."
    )


def test_is_dovetail_simple():
    # Based on the GFA 2 specification's rules:
    # https://gfa-spec.github.io/GFA-spec/GFA2.html#edge
    #
    # And, more specifically, these match the four cases
    # outlined in https://github.com/GFA-spec/GFA-spec/issues/133

    # Same orientation: beg1 = 0 and end2 = y$ (--)
    #
    # Looks like
    #         |  |
    # 1. <--------
    # 2.      <--------
    assert gu.is_dovetail("-", "-", "0", "5", "7", "9$")

    # Same orientation: beg2 = 0 and end1 = x$ (++)
    #
    # Looks like
    #         |  |
    # 1. -------->
    # 2.      -------->
    assert gu.is_dovetail("+", "+", "1", "3$", "0", "4")

    # Opposite orientations: beg1 = 0 and beg2 = 0 (-+)
    #
    # Looks like
    #         |  |
    # 1. <--------
    # 2.      -------->
    assert gu.is_dovetail("-", "+", "0", "3", "0", "4")

    # Opposite orientations: end1 = x$ and end2 = y$ (+-)
    #
    # Looks like
    #         |  |
    # 1. -------->
    # 2.      <--------
    assert gu.is_dovetail("+", "-", "2", "3$", "2", "4$")


def test_is_dovetail_degenerate():
    # See https://github.com/GFA-spec/GFA-spec/issues/133
    #
    # BASICALLY: for the four "good" cases above, there are also
    # mirror cases with negated orientations where the GFA rules
    # are technically followed but the edges are not really dovetails (at
    # least, not in my opinion).
    #
    # For now, we do NOT allow these degenerate cases to count as dovetails.
    # This may change in the future (or maybe will do something fancy like
    # detect these cases and swap edge orders to make them into dovetails)
    # but for now let's test that these are not allowed.

    # Same orientation: beg1 = 0 and end2 = y$ BUT ++ instead of --
    #
    # Looks like
    #    |  |
    # 1. -------->       |  |
    # 2.            -------->
    assert not gu.is_dovetail("+", "+", "0", "3", "5", "8$")

    # Same orientation: beg2 = 0 and end1 = x$ BUT -- instead of ++
    #
    # Looks like
    #    |  |
    # 1. <--------       |  |
    # 2.            <--------
    assert not gu.is_dovetail("-", "-", "5", "8$", "0", "3")

    # Opposite orientations: beg1 = 0 and beg2 = 0 BUT +- instead of -+
    #
    # Looks like
    #    |  |
    # 1. -------->       |  |
    # 2.            <--------
    assert not gu.is_dovetail("-", "-", "0", "3", "0", "4")

    # Opposite orientations: end1 = x$ and end2 = y$ BUT -+ instead of +-
    #
    # Looks like
    #    |  |
    # 1. <--------       |  |
    # 2.            -------->
    assert not gu.is_dovetail("-", "+", "5", "8$", "5", "8$")


def test_is_dovetail_bad_orientations():
    with pytest.raises(GraphParsingError) as ei:
        gu.is_dovetail("+", "X", "0", "3", "5", "8$")
    assert str(ei.value) == 'Unrecognized edge orientation(s): "+" -> "X"'

    with pytest.raises(GraphParsingError) as ei:
        gu.is_dovetail("X", "-", "0", "3", "5", "8$")
    assert str(ei.value) == 'Unrecognized edge orientation(s): "X" -> "-"'

    with pytest.raises(GraphParsingError) as ei:
        gu.is_dovetail("", "", "0", "3", "5", "8$")
    assert str(ei.value) == 'Unrecognized edge orientation(s): "" -> ""'
