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
####
# Tests some corner cases for edge counts/etc.
# TODO: add test case for duplicate edges once #75 (see GitHub) is resolved.

import contextlib
from metagenomescope.tests import utils


def test_self_implying_edges():
    connection, cursor = utils.create_and_open_db("loop.gfa")
    with contextlib.closing(connection):
        utils.validate_std_counts(cursor, 4, 6, 6)
