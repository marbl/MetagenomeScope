#!/usr/bin/env python
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
# Generates a copy of the viewer interface index.html page where the demo files
# available to select in the "Demo .db" dialog match those in a specified list.
# Right now the input list is a tab-separated values (TSV) file, where each
# line (corresponding to a single .db file) is formatted as
# filename (tab) description".
#
# (Descriptions can include HTML, e.g. for hyperlinks to the data source.)
#
# By default, makes the first .db file's radio button checked.

import argparse

# Based on indent level for <div class="radio"> elements in the HTML file
DB_HTML_MARGIN = "                        "
DB_HTML_TEMPLATE = """
                        <div class="radio">
                            <label>
                                <input type="radio" name="fs" id="{ID}"{CHECKED}>
                                {DESC}
                            </label>
                        </div>\n"""
# Shift the checked="checked" property declaration up two indent levels to make
# it flush with the <input type="radio"> tag
CHECKED = "\n" + DB_HTML_MARGIN + (" " * 8) + "checked=\"checked\""
DB_LIST_START_TAG = "<!-- BEGIN DEMO .DB LIST -->"
DB_LIST_END_TAG = "<!-- END DEMO .DB LIST -->"


parser = argparse.ArgumentParser(description="Generates a copy of the " + \
        "MetagenomeScope index.html page with a specified demo .db list.")
parser.add_argument("-i", "--inputfile", required=True,
        help="demo .db list file")
parser.add_argument("-v", "--indexfile", required=True,
        help="viewer interface index.html file to use as a template (this file will not be modified) -- must be non-minified")
parser.add_argument("-o", "--outputfile", required=True,
        help="output index.html file name (cannot be the same filename as the template file)")
args = parser.parse_args()

db_ct = 0
html_output = ""
with open(args.inputfile, "r") as db_list_file:
    for line in db_list_file:
        if "\t" in line:
            db_fn, db_desc = line.split("\t")
            # Fill in appropriate information in DB_HTML_TEMPLATE
            db_html_output = DB_HTML_TEMPLATE.replace("{ID}", db_fn)
            db_html_output = db_html_output.replace("{DESC}", db_desc.strip())
            if db_ct == 0:
                db_html_output = db_html_output.replace("{CHECKED}", CHECKED)
            else:
                db_html_output = db_html_output.replace("{CHECKED}", "")
            html_output += db_html_output
            db_ct += 1

# We've got the HTML corresponding to the demo .db list (html_output) ready.
# Now we just need to insert it into index.html in the right place.
# NOTE there's almost certainly a more efficient way to write this without
# checking every line in the file for the BEGIN DEMO .DB LIST comment, but
# considering the size of the index.html file this shouldn't be that slow
with open(args.outputfile, "w") as output_index_file:
    with open(args.indexfile, "r") as template_index_file:
        going_through_template_demo_list = False
        for line in template_index_file:
            if not going_through_template_demo_list:
                if DB_LIST_START_TAG in line:
                    output_index_file.write(DB_HTML_MARGIN + DB_LIST_START_TAG)
                    output_index_file.write(html_output)
                    going_through_template_demo_list = True
                else:
                    output_index_file.write(line)
            else:
                if DB_LIST_END_TAG in line:
                    output_index_file.write(DB_HTML_MARGIN + DB_LIST_END_TAG +
                            "\n")
                    going_through_template_demo_list = False
print "Demo .db list containing %d files inserted into output file %s." % \
        (db_ct, args.outputfile)
