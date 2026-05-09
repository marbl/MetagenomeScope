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

from metagenomescope import gfa_utils as gu


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
