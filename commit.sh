#! /usr/bin/env bash
# Assumes the CWD is the root of the MetagenomeScope/ repository.
bash minify_files.fish
git add viewer/js/xdot2cy.min.js
git add viewer/css/viewer_style.min.css
git add viewer/index.min.html
git commit
