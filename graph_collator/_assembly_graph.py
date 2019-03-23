# Copyright (C) 2017-2019 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
# Describes an AssemblyGraph object in a reasonable way. This should be
# applicable to any assembly graph, but I'm explictly planning on it supporting
# LastGraph, GML (MetaCarvel output), GFA, and FASTG (SPAdes/MEGAHIT/etc.
# output) files.


class AssemblyGraph(object):
    """A class that stores information about an assembly graph.

       (The hope is that this will be a cleaner approach than storing a billion
       different variable names that define the various attributes of a graph.)
    """

    def __init__(self, filename, filetype):
        """Initializes the AssemblyGraph object.

           I imagine instances of this class will be iteratively updated
           as the assembly graph reader goes through a file, so this doesn't
           require the user to declare a lot about the AssemblyGraph up front.
        """
        self.filename = filename
        self.filetype = filetype
