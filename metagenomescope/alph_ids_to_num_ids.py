#!/usr/bin/env python3
# Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
# Contains convert(), which converts GFA files with non-numeric IDs to GFA
# files with numeric IDs. See the function docstring for more information.


def convert(input_gfa_filename, output_gfa_filename):
    """Writes a converted version of the input GFA file to the output filename.

       Returns a dict mapping original contig IDs to their numerical
       counterparts.
    """
    alph_id_to_num_id = {}
    contigs_seen = 1
    new_file_text = ""
    with open(input_gfa_filename, "r") as graphfile:
        for line in graphfile.readlines():
            if line[0] == "S":
                line_parts = line.strip().split("\t")
                alph_id_to_num_id[line_parts[1]] = contigs_seen
                new_file_text += line.replace(line_parts[1], str(contigs_seen))
                contigs_seen += 1
            elif line[0] == "L":
                line_parts = line.strip().split("\t")
                new_src_id = str(alph_id_to_num_id[line_parts[1]])
                new_tgt_id = str(alph_id_to_num_id[line_parts[3]])
                new_link_line = line.replace(line_parts[1], new_src_id)
                new_file_text += new_link_line.replace(
                    line_parts[3], new_tgt_id
                )
            else:
                new_file_text += line
    with open(output_gfa_filename, "w") as outfile:
        outfile.write(new_file_text)
    return alph_id_to_num_id
