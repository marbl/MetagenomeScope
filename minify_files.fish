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
set -l attribution "/* Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
 */"
set -l hattribution "<!doctype html>
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
-->"
echo $attribution > viewer/js/xdot2cy.min.js
echo $attribution > viewer/css/viewer_style.min.css
echo $hattribution > viewer/index.min.html
csso viewer/css/viewer_style.css >> viewer/css/viewer_style.min.css
uglifyjs viewer/js/xdot2cy.js >> viewer/js/xdot2cy.min.js
html-minifier --html5 --minify-css --minify-js --remove-comments --collapse-whitespace viewer/index.html | tail -c +16 >> viewer/index.min.html
# Add references to minified xdot2cy.js and viewer_style.css files in the
# minified HTML file.
sed -i -e 's/xdot2cy\.js/xdot2cy\.min\.js/g' viewer/index.min.html
sed -i -e 's/viewer_style\.css/viewer_style\.min\.css/g' viewer/index.min.html
echo "File minification complete."
echo "Make sure that the version of index.min.html you're uploading somewhere is renamed to index.html in its new location."
