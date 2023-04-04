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

# Import submodules so they're easy to see from REPL
from . import (
    arg_utils,
    parsers,
    config,
    file_utils,
    input_node_utils,
    layout_utils,
    msg_utils,
)

# ... And explicitly declare them in __all__. This will stop flake8 from
# yelling at us about these imports being unused.
__all__ = [
    "arg_utils",
    "parsers",
    "config",
    "file_utils",
    "input_node_utils",
    "layout_utils",
    "msg_utils",
]
