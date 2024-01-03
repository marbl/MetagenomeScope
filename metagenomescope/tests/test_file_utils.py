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

import os
import tempfile
import pytest
from metagenomescope import file_utils


def test_create_output_dir():
    # Test creating multiple dirs at once using makedirs
    with tempfile.TemporaryDirectory() as tmpdir:
        file_utils.create_output_dir("{}/mgsc-def/mgsc-ghi".format(tmpdir))
        assert os.listdir(tmpdir) == ["mgsc-def"]
        assert os.listdir("{}/mgsc-def".format(tmpdir)) == ["mgsc-ghi"]
        assert os.listdir("{}/mgsc-def/mgsc-ghi".format(tmpdir)) == []

        # Test error raised if directory exists (this functionality actually
        # doesn't come from our code, it's just a freebie thanks to python)
        with pytest.raises(FileExistsError) as e:
            file_utils.create_output_dir(tmpdir)
        # the actual error message includes some extra text (e.g. "[Errno 17]")
        # so we get around this by just checking part of the message looks ok
        assert "File exists: '{}'".format(tmpdir) in str(e.value)
