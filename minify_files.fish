#! /usr/bin/fish
# Minifies the custom JavaScript and CSS code in MetagenomeScope.
#
# Assumes the CWD is the root of the MetagenomeScope/ repository.
# Also assumes that csso-cli, uglify-js, and html-minifier have been installed
# through NPM with the -g option enabled.
# Also assumes that the doctype in index.html is exactly 15 characters long.
# (The doctype has to be the first element in the minified HTML file, but we
# want to also include the attribution; our solution here is to manually insert
# the doctype and attribution, and then remove the now-redundant copy of the
# doctype in the minified HTML.)

set -l attribution '/* Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
 */'
set -l hattribution '<!doctype html>
<!--
    Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
-->'
echo $attribution > viewer/js/xdot2cy.min.js
echo $attribution > viewer/css/viewer_style.min.css
echo $hattribution > viewer/index.min.html
csso viewer/css/viewer_style.css >> viewer/css/viewer_style.min.css
uglifyjs viewer/js/xdot2cy.js >> viewer/js/xdot2cy.min.js
html-minifier --html5 --minify-css --minify-js --remove-comments --collapse-whitespace viewer/index.html | tail -c +16 >> viewer/index.min.html

# Add references to minified xdot2cy.js and viewer_style.css files in the
# minified HTML file.
#
# We provide an empty extension for the -i argument since some platforms'
# versions of sed explicitly require a suffix argument for -i.
# CODELINK: See http://www.grymoire.com/Unix/Sed.html#uh-62h (c/o Bruce
# Barnett) for more info on -i and which platforms require this argument.
sed -i'' 's/xdot2cy\.js/xdot2cy\.min\.js/g' viewer/index.min.html
sed -i'' 's/viewer_style\.css/viewer_style\.min\.css/g' viewer/index.min.html

# Set up the Electron version of the index.
#
# Step 1 is to replace the script tag that loads jQuery with a script that
# loads jQuery via require().
#
# CODELINK: jQuery loading solution for Electron using require() c/o Jocelyn
# Badgely (GitHub username "Twipped")'s answer here:
# https://github.com/electron/electron/issues/254
set -l jqueryrequire '<script>window\.\$ = window\.jQuery = require(\'\.\.\/viewer\/js\/jquery-\1\.min\.js\');<\/script>'
cp viewer/index.min.html electron/index.min.html
sed -i'' "s/<script src=[\"\']js\/jquery-\([0-9\.]*\).min\.js[\"\']><\/script>/$jqueryrequire/" electron/index.min.html

# Step 2 in setting up the Electron version is to replace all references to the
# js/ and css/ directories with references to ../viewer/js/, or ../viewer/css/.
# Fortunately, this is a bit less crazy than the above sed invocation.
#
# To make things a bit clearer: the first capture group in the regex we use for
# this is either "src" or "href". The second capture group is the string being
# used to start the filename: either " or '. The third capture group is the code
# directory's name: either "js" or "css".
sed -i'' 's/\(src\|href\)=\([\"\']\)\(js\|css\)\//\1=\2\.\.\/viewer\/\3\//g' electron/index.min.html

# Step 3: just remove the shortcut icon thing, since it isn't used by Electron
# and we don't have bubble.ico in the electron/ folder anyway
sed -i'' 's/<link rel=\"shortcut icon\" href=\"bubble\.ico\">//' electron/index.min.html

# Finally, print ending messages
echo "File minification complete."
echo "Make sure that the version of index.min.html you're uploading somewhere is renamed to index.html in its new location."
