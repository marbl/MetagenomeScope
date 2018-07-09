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
DB_HTML_TEMPLATE = """                        <div class="radio">
                            <label>
                                <input type="radio" name="fs" id="{ID}"{CHECKED}>
                                {DESC}
                            </label>
                        </div>\n"""
# Shift the checked="checked" property declaration up two indent levels to make
# it flush with the <input type="radio"> tag
CHECKED = "\n" + (" " * 32) + "checked=\"checked\""
DB_LIST_START_TAG = "<!-- BEGIN DEMO .DB LIST -->"
DB_LIST_END_TAG = "<!-- END DEMO .DB LIST -->"

parser = argparse.ArgumentParser(description="Generates a copy of the " + \
        "MetagenomeScope index.html page with a specified demo .db list.")
parser.add_argument("-l", "--listfile", required=True,
        help="demo .db list file")
parser.add_argument("-f", "--htmlfile", required=True,
        help="(non-minified) index.html file to insert the HTML demo list into")
args = parser.parse_args()

db_ct = 0
list_html_output = ""
with open(args.listfile, "r") as db_list_file:
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
            list_html_output += db_html_output
            db_ct += 1

# We've got the HTML corresponding to the demo .db list (list_html_output)
# ready. Now we just need to insert it into index.html in the right place.
with open(args.htmlfile, "r") as htmlfile:
    html_file_text = htmlfile.readlines()
with open(args.htmlfile, "w") as htmlfile:
    going_through_template_demo_list = False
    for line in html_file_text:
        if not going_through_template_demo_list:
            htmlfile.write(line)
            if DB_LIST_START_TAG in line:
                htmlfile.write(list_html_output)
                going_through_template_demo_list = True
        else:
            # Don't write anything extra until we reach the end tag
            if DB_LIST_END_TAG in line:
                htmlfile.write(line)
                going_through_template_demo_list = False
print "HTML Demo .db list specifying %d .db files inserted into file %s." % \
        (db_ct, args.htmlfile)
