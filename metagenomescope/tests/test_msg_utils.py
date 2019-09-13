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
# Tests the various (very simple) functions in msg_utils.py.
#
# CODELINK: Uses of capsys were based on
# https://docs.pytest.org/en/latest/capture.html (section "Accessing captured
# output from a test function").

import pytest
from metagenomescope import msg_utils
from metagenomescope.config import DONE_MSG

def test_operation_msg(capsys):
    msg_utils.operation_msg("message test")
    captured = capsys.readouterr()
    assert captured.out == "message test "

    msg_utils.operation_msg("test123123", newline=True)
    captured = capsys.readouterr()
    assert captured.out == "test123123\n"

    msg_utils.operation_msg("this is a ws test  ! \t", newline=True)
    captured = capsys.readouterr()
    assert captured.out == "this is a ws test  ! \t\n"

    msg_utils.operation_msg("   as  isthis   ", newline=True)
    captured = capsys.readouterr()
    assert captured.out == "   as  isthis   \n"


def test_conclude_msg(capsys):
    msg_utils.conclude_msg()
    captured = capsys.readouterr()
    assert captured.out == (DONE_MSG + "\n")

    msg_utils.conclude_msg("Just prints arbitrary stuff. This is simple.")
    captured = capsys.readouterr()
    assert captured.out == "Just prints arbitrary stuff. This is simple.\n"
