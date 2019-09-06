#! /usr/bin/env bash
# Minifies the custom JavaScript and CSS code in MetagenomeScope.
#
# PREREQUISITES:
# -Assumes the CWD is the root of the MetagenomeScope/ repository.
#
# -Also assumes that csso-cli, uglify-js, and html-minifier have been installed
# through NPM with the -g option enabled.
#
# -Also assumes that, if you're running this on a macOS computer, gnu-sed has
# been installed as gsed. See the comment labelled "SEDTHING" (you can Ctrl-F
# for that in this file) for more details on why this is necessary.
#
# -Also assumes that the doctype in index.html is exactly 15 characters long.
# (The doctype has to be the first element in the minified HTML file, but we
# want to also include the attribution; our solution here is to manually insert
# the doctype and attribution, and then remove the now-redundant copy of the
# doctype in the minified HTML.)

# Allow aliases set in this script to be used later on in this script.
# Solution from https://stackoverflow.com/a/3354931.
shopt -s expand_aliases

# Use of heredoc + read to assign multiline strings to a variable based on
# https://stackoverflow.com/a/23930212/10730311.
read -r -d '' attribution << ATTRIBUTION_END
/* Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 */
ATTRIBUTION_END

read -r -d '' htmlattribution << ATTRIBUTION_END
<!doctype html>
<!--
    Copyright (C) 2016- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
    Authored by Marcus Fedarko
 
    This file is part of MetagenomeScope.

    MetagenomeScope is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    MetagenomeScope is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
-->
ATTRIBUTION_END

# Write attributions to minified files.
echo "$attribution" > viewer/js/xdot2cy.min.js
echo "$attribution" > viewer/css/viewer_style.min.css
echo "$htmlattribution" > viewer/index.min.html
# Actually minify the files, and append them after the attributions.
csso viewer/css/viewer_style.css >> viewer/css/viewer_style.min.css
uglifyjs viewer/js/xdot2cy.js >> viewer/js/xdot2cy.min.js
html-minifier --html5 --minify-css --minify-js --remove-comments --collapse-whitespace viewer/index.html | tail -c +16 >> viewer/index.min.html

# SEDTHING: To make a long story short: the macOS version of "sed" differs a
# bit from the GNU version of "sed". This impacts this script in the way
# that the -i option is used: -i '' works on the macOS computer I'm testing
# this on, and fails on the Linux computer I'm testing this on, while -i''
# works on Linux but fails on macOS (at least for my N=2 computer sample size).
#
# A way to circumvent this problem is using the GNU sed version on macOS, aka
# "gsed" (which is available through Homebrew as gnu-sed, as of writing this).
# CODELINK: Idea to use gsed if available c/o Sruthi Poddutur's answer to this
# Stack Overflow question: https://stackoverflow.com/questions/4247068/
# Link to Sruthi's SO profile:
# https://stackoverflow.com/users/7362778/sruthi-poddutur
#
# Note that we redirect which's output to /dev/null so that it doesn't print
# the location of gsed (if it has one) to stdout.
if which gsed > /dev/null
then
    alias mgsc_sed="gsed"
else
    alias mgsc_sed="sed"
fi

# Add references to minified xdot2cy.js and viewer_style.css files in the
# minified HTML file.
#
# We provide an empty extension argument for the -i argument so that sed
# doesn't create backup files.
# CODELINK: See http://www.grymoire.com/Unix/Sed.html#uh-62h (c/o Bruce
# Barnett) for more info on -i and which platforms require this argument.
mgsc_sed -i'' 's/xdot2cy\.js/xdot2cy\.min\.js/g' viewer/index.min.html
mgsc_sed -i'' 's/viewer_style\.css/viewer_style\.min\.css/g' viewer/index.min.html

# Instrument JS code. This is inefficient because it also instruments the
# minified JS files, which is unnecessary -- a TODO is fixing that.
nyc instrument viewer/js/ viewer/instrumented_js/

# Set up version of index.html for running tests headlessly
cp viewer/index.html viewer/headless_tests_index.html
# first difference: the headless version automatically invokes mgsc.runTests(),
# while the normal version doesn't.
mgsc_sed -i'' 's/<script id=\"runTestsHere\">/<script id=\"runTestsHere\">mgsc.runTests();/' viewer/headless_tests_index.html
# second difference: the headless version uses an instrumented version of the
# JS code
mgsc_sed -i'' 's/js\/xdot2cy\.js/instrumented_js\/xdot2cy\.js/g' viewer/headless_tests_index.html

# Finally, print ending messages
echo "File minification complete."
echo "Make sure that the version of index.min.html you're uploading somewhere is renamed to index.html in its new location."
