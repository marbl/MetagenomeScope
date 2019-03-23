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
# Reads in an assembly graph.


import _assembly_graph
import config

class AssemblyGraphParser(object):

    def __init__(self, filename, ububbles_labels=False,
                 upatterns_labels=False):
        """Initializes a parser for a given assembly graph filename.

           Once this parser has been initialized, you can call parse() to
           actually go through and read the file, updating this parser's graph
           attribute accordingly.
        """
        self.filename = filename
        filename_lowercase = self.filename.lower()

        # We'll set this to True if we need to populate nodelabel2obj.
        # I imagine that the graph object should have
        # nodeid2obj/nodelabel2obj/etc as various attributes.
        self.need_label_mapping = False

        # Determine filetype
        filetype = None
        for fsuffix in config.FILESUFFIX2TYPE:
            if filename_lowercase.endswith(fsuffix):
                self.filetype = config.FILESUFFIX2TYPE[fsuffix]
                break
        if self.filetype is None:
            raise(IOError, config.FILETYPE_ERR)

        # Ensure that the -ubl/-upl options are only used when the input graph
        # is of a type that accepts labels.
        if ububbles_labels or upatterns_labels:
            if self.filetype != "GML":
                raise(ValueError, config.LABEL_EXISTENCE_ERR)
            self.need_label_mapping = True

        # Now that we've determined the graph filetype, we can parse the graph
        # accordingly
        self.graph = _assembly_graph.AssemblyGraph(filename, filetype)

    def parse(self):
        """Figures out what parsing function to call and then calls it."""
        if self.graph.filetype == "LastGraph":
            self.parse_LastGraph()
        elif self.graph.filetype == "GML":
            self.parse_GML()
        elif self.graph.filetype == "GFA":
            self.parse_GFA()
        elif self.graph.filetype == "FASTG":
            self.parse_FASTG()
        else:
            raise IOError, "Graph filetype incorrectly set before parsing"
        
    def parse_LastGraph(self):
        """Parses a LastGraph file."""
        with open(self.graph.filename, 'r') as assembly_file:
            pass

    def parse_GML(self):
        """Parses a GML file."""
        pass

    def parse_GFA(self):
        """Parses a GFA file."""
        pass

    def parse_FASTG(self):
        """Parses a FASTG file."""
        pass
