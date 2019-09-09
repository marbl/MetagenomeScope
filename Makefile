# Since the bulk of MetagenomeScope's code isn't compiled, this Makefile just
# performs a few actions using the following (phony) targets:
#
# test: Runs the python and viewer tests.
#
# pytest: Runs all preprocessing script tests using pytest.
#
# spqrtest: Runs the SPQR-specific preprocessing script tests using pytest.
#
# viewertest: Minifies web code (and instruments JS code) and creates/updates
#  viewer/headless_tests_index.html, then runs the viewer interface tests
#  using mocha-headless-chrome.
#
# spqr: this is used to compile the "SPQR script" (metagenomescope/spqr.cpp).
#  NOTE that compiling the SPQR script is only necessary if you want to use
#  the -spqr option of the preprocessing script (mgsc).
#  See https://github.com/marbl/MetagenomeScope/wiki/Installation-Instructions
#  for details on this option.
#
# stylecheck: Checks to make sure that the Python and JavaScript codebases are
#  properly formatted. Requires that a few extra packages are installed.
#  This directive was taken from Qurro's Makefile.
#
# style: Auto-formats code to make it (mostly) compliant with stylecheck.
#  Requires that a few extra packages are installed. This directive was taken
#  from Qurro's Makefile.

.PHONY: pytest spqrtest viewertest test spqr

# This might have to be changed depending on your system. When I tried
# compiling this on a Mac computer, the g++ binary seemed to just redirect to
# clang, and that in turn seemed to fail to link with the C++ libraries.
# Explicitly installing "gcc49" via homebrew -- and calling it via g++-4.9 --
# solved this problem for me.
COMPILER = g++
# Omitting optimization and warning flags for the time being; adding those
# later would be a good idea.
CFLAGS = -std=gnu++11

# NOTE modify this to point to the include directory of OGDF on your system
IDIR = ~/OGDF/include
# NOTE modify this to point to the _release directory of OGDF on your system
RDIR = ~/OGDF/_release

OGDF_INCL = -I $(IDIR)
OGDF_LINK = -L $(RDIR)

# Set per http://amber-v7.cs.tu-dortmund.de/doku.php/tech:installgcc
OGDF_FLAGS = $(OGDF_INCL) $(OGDF_LINK) -l OGDF -pthread
# Apparently forward-slashes should work on Windows systems as well as
# Linux/OS X systems. We don't officially support Windows, so it shouldn't make
# a difference.
SCRIPT_DIR = metagenomescope/
SPQR_CODE = $(addprefix $(SCRIPT_DIR), spqr.cpp)
SPQR_BINARY = $(addprefix $(SCRIPT_DIR), spqr)

PYTEST_COMMAND = python3 -B -m pytest metagenomescope/tests/ --cov
PYLOCS = metagenomescope/ setup.py viewer/populate_demo.py
JSLOCS = viewer/js/xdot2cy.js viewer/tests/*.js docs/js/extra_functionality.js .jshintrc
HTMLCSSLOCS = viewer/index.html viewer/404.html viewer/css/viewer_style.css docs/404.html docs/index.html docs/css/mgsc_docs_style.css

# -B: don't create __pycache__/ directories
pytest:
	$(PYTEST_COMMAND)
	rm metagenomescope/tests/output/*

spqrtest:
	$(PYTEST_COMMAND) -m "spqrtest"
	rm metagenomescope/tests/output/*

viewertest:
	bash minify_files.sh
	mocha-headless-chrome -f viewer/headless_tests_index.html -c js_coverage.json

test: pytest viewertest

spqr:
	$(COMPILER) $(SPQR_CODE) $(CFLAGS) $(OGDF_FLAGS) -o $(SPQR_BINARY)

stylecheck:
	flake8 --ignore=E203,W503,E266,E501 $(PYLOCS)
	black --check -l 79 $(PYLOCS)
	jshint $(JSLOCS)
	prettier --check --tab-width 4 $(JSLOCS) $(HTMLCSSLOCS)

style:
	black -l 79 $(PYLOCS)
	@# To be extra safe, do a dry run of prettier and check that it hasn't
	@# changed the code's abstract syntax tree (AST). (Black does this sort of
	@# thing by default.)
	prettier --debug-check --tab-width 4 $(JSLOCS) $(HTMLCSSLOCS)
	prettier --write --tab-width 4 $(JSLOCS) $(HTMLCSSLOCS)
