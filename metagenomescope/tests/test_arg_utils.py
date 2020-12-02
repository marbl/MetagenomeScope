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
# Tests the various (very simple) functions in arg_utils.py.

import tempfile
import pytest
from metagenomescope import arg_utils

def test_validate_max_counts():
    # Both bad
    with pytest.raises(ValueError) as e:
        arg_utils.validate_max_counts(-1, -1)
    assert "Maximum node / maximum edge counts must be at least 1" == str(e.value)

    # Just node ct bad
    with pytest.raises(ValueError) as e:
        arg_utils.validate_max_counts(-100, 5)
    assert "Maximum node count must be at least 1" == str(e.value)

    # Just edge ct bad
    with pytest.raises(ValueError) as e:
        arg_utils.validate_max_counts(1, 0)
    assert "Maximum edge count must be at least 1" == str(e.value)

    # Both good
    arg_utils.validate_max_counts(1, 1)

def test_check_dir_existence():
    # Check failure case -- directory path already exists.
    # Based on https://docs.python.org/3/library/tempfile.html#examples
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileExistsError) as e:
            arg_utils.check_dir_existence(tmpdir)
        assert "Output directory {} already exists.".format(tmpdir) == str(e.value)

    # Check success case -- path does not already exist.
    # If this test breaks for you then uhhhh I guess submit a PR and ask me to
    # rewrite this test lol, sorry
    arg_utils.check_dir_existence("./this-should-not-exist-if-it-does-oh-no/")
