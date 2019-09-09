#!/usr/bin/env python3
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
# Generates a copy of the viewer interface index.html page where the demo files
# available to select in the "Demo .db" dialog match those in a specified list.
# Right now the input list is a tab-separated values (TSV) file, where each
# line (corresponding to a single .db file) is formatted as
# filename[(tab)description]".
#
# (Descriptions can include HTML, e.g. for hyperlinks to the data source.)
#
# By default, makes the first .db file's radio button checked.

import argparse
import os
import sqlite3

# This is used to modify the #demoDir span in the index.html file based on the
# path specified by -hd.
HOST_DB_DIR_TEMPLATE = (
    '                        <span id="demoDir" data-mgscdbdirectory="{}"\n'
)
HOST_DB_DIR_TAG = '<span id="demoDir"'
# Based on indent level for <div class="radio"> elements in the HTML file
DB_HTML_TEMPLATE = """                        <div class="radio">
                            <label>
                                <input type="radio" name="fs" id="{ID}"{CHECKED}>
                                {DESC}
                            </label>
                        </div>\n"""
# Shift the checked="checked" property declaration up two indent levels to make
# it flush with the <input type="radio"> tag
CHECKED = "\n" + (" " * 32) + 'checked="checked"'
DB_LIST_START_TAG = "<!-- BEGIN DEMO .DB LIST -->"
DB_LIST_END_TAG = "<!-- END DEMO .DB LIST -->"

parser = argparse.ArgumentParser(
    description="""Generates a copy of a provided
        MetagenomeScope index.html page with a demo listing certain .db
        files."""
)
parser.add_argument(
    "-d",
    "--dbdirectory",
    required=True,
    help="""directory containing all .db files that will be referenced in
        the generated demo.""",
)
parser.add_argument(
    "-l",
    "--listfile",
    required=False,
    help="""optional file where each line defines a .db file to be included
        in the generated demo. Each line is of the format
        filename(tab)description
        where "filename" is the name of a .db file located within the directory
        specified by -d, "description" is an optional description of the .db
        file specified on that line, and "(tab)" is a tab character (only
        required if a description is given). If this is not specified, then all
        .db files in the directory specified by -d will be included in the
        demo.""",
)
parser.add_argument(
    "-i",
    "--indexfile",
    required=True,
    help="""(non-minified) index.html file to use as a base for the new
        index.html file. If no output index file is specified via -o, then the
        demo information will be inserted into this index file; if an output
        index file is specified, though, then this file will not be changed
        (unless you give the same file as the argument to both -i and -o).""",
)
parser.add_argument(
    "-o",
    "--outputindexfile",
    required=False,
    help="""output index.html file containing the new demo information;
        if this is not specified, then the new index.html page containing the
        demo information will be written to the index.html file specified by
        -i.""",
)
parser.add_argument(
    "-hd",
    "--hostdbdirectory",
    required=False,
    default="db",
    help="""directory containing the hosted .db files (relative to the
        location of the index.html file). Defaults to "db", but you can
        change that depending on where you want to store the .db files on your
        hosted version of the viewer interface.""",
)

args = parser.parse_args()

dbfn2desc = {}
# We use this list (instead of just using dbfn2desc.keys()) in order to
# preserve the order in the list file.
filename_list = []
list_html_output = ""
if args.listfile is not None:
    with open(args.listfile, "r") as db_list_file:
        for line in db_list_file:
            if "\t" in line:
                db_fn, db_desc = line.split("\t")
                dbfn2desc[db_fn] = db_desc.strip()
                filename_list.append(db_fn)
            else:
                # It's possible for the user to avoid specifying a file
                # description. In this case, we check that this line isn't just
                # a blank line; if so, then we just read the entire line as the
                # file name. (We also set the "description" as the file name,
                # matching the output of this script when no list file is
                # provided.)
                db_fn = line.strip()
                if len(db_fn) > 0:
                    dbfn2desc[db_fn] = db_fn
                    filename_list.append(db_fn)

db_ct = 0
if args.listfile is None:
    filename_list = os.listdir(args.dbdirectory)
for fn in filename_list:
    # This check is mainly for the case where no list file is given and we just
    # iterate over all the .db files in the given directory. However, it's also
    # used when looking at the list file, so if the user specifies a non-.db
    # file in the list file then this check also ensures it'll ignored.
    if fn.endswith(".db"):
        # If the user didn't specify a list file (-l), then just use all .db
        # files in the given directory (in this case, args.listfile will be
        # None). However, if the user did specify a list file, then we only
        # use those .db files that were specified in the list file (and their
        # filenames are therefore now keys in dbfn2desc).
        if args.listfile is None or fn in dbfn2desc:
            # We're going to include this .db file in the demo list!
            # Get data from this .db file
            connection = sqlite3.connect(os.path.join(args.dbdirectory, fn))
            cursor = connection.cursor()
            # print fn
            try:
                cursor.execute(
                    "SELECT filetype, node_count, edge_count from assembly;"
                )
            except sqlite3.OperationalError as e:
                # Accounts for when the specified database file doesn't have
                # an "assembly" table. Also happens when the database file
                # didn't exist (because trying to access it using sqlite3 will
                # create it, and then the same problem of no assembly data
                # happens).
                raise sqlite3.OperationalError("%s: %s" % (fn, e))
            data = cursor.fetchone()
            if data is None:
                raise ValueError("%s doesn't have assembly data" % (fn))
            # Use this data to populate the parenthetical descriptions
            # Uses the str.format() python builtin to ensure that node and edge
            # counts use commas as the thousands separator
            contig_noun = "contigs"
            edge_noun = "edges"
            if data[0] in ("LastGraph", "GFA", "FASTG"):
                contig_noun = "positive contigs"
                edge_noun = "positive edges"
            main_desc = fn if args.listfile is None else dbfn2desc[fn]
            db_desc = "{} ({}, {:,} {}, {:,} {})".format(
                main_desc, data[0], data[1], contig_noun, data[2], edge_noun
            )
            # Fill in appropriate information in DB_HTML_TEMPLATE
            checked_str = CHECKED if db_ct == 0 else ""
            db_html_output = DB_HTML_TEMPLATE.format(
                ID=fn, DESC=db_desc, CHECKED=checked_str
            )
            list_html_output += db_html_output
            db_ct += 1

if db_ct == 0:
    raise ValueError('Directory "%s" has no .db files' % (args.dbdirectory))

# We've got the HTML corresponding to the demo .db list (list_html_output)
# ready. Now we just need to insert it into index.html in the right place.

# Read the input file's contents into memory. It shouldn't be that large, so
# this shouldn't pose a problem.
with open(args.indexfile, "r") as indexfile:
    html_file_text = indexfile.readlines()

# Figure out where we're going to be outputting the finished HTML to. Depending
# on what the user specified, it could be on top of the input index file or in
# an entirely new file.
if args.outputindexfile is None:
    output_file_path = args.indexfile
else:
    output_file_path = args.outputindexfile

# In any case, we've got the output path figured out now; all that's left to do
# is write the input file to it (with the new demo HTML included).
with open(output_file_path, "w") as outputindexfile:
    going_through_template_demo_list = False
    done_with_template_demo_list = False
    done_with_hd_modification = False
    for line in html_file_text:
        if not going_through_template_demo_list:
            if not done_with_hd_modification and HOST_DB_DIR_TAG in line:
                # TODO make -hd default just be keeping the value the same as in
                # the passed index.html file?
                # In that case, we'd remove the default option on -hd. that
                # should make it None IIRC but check.
                # And if -hd is None, then just skip this conditional and write
                # the line like normal; I guess we could do this via
                # making the first conditional of this "if" be hd is not None.
                outputindexfile.write(
                    HOST_DB_DIR_TEMPLATE.format(args.hostdbdirectory)
                )
                done_with_hd_modification = True
                continue
            else:
                outputindexfile.write(line)
            if not done_with_template_demo_list and DB_LIST_START_TAG in line:
                outputindexfile.write(list_html_output)
                going_through_template_demo_list = True
        else:
            # Don't write anything extra until we reach the end tag
            if DB_LIST_END_TAG in line:
                outputindexfile.write(line)
                going_through_template_demo_list = False
                done_with_template_demo_list = True
if args.outputindexfile is None:
    print(
        "Demo .db list of %d .db files inserted into %s."
        % (db_ct, args.indexfile)
    )
else:
    print(
        "Copy of %s with demo .db list of %d .db files written to %s."
        % (args.indexfile, db_ct, args.outputindexfile)
    )
