# Since the bulk of MetagenomeScope's code isn't compiled, this Makefile only
# performs a few actions using the following (phony) targets:
#
# test: Runs the general, spqr, and viewer tests.
#
# generaltest: Runs the non-SPQR preprocessing script tests using pytest.
#
# spqrtest: Runs the SPQR-specific preprocessing script tests using pytest.
#
# viewertest: Runs the viewer interface tests using mocha-headless-chrome.
#  (If you don't have mocha-headless-chrome installed, you can install it via
#  "npm install -g mocha-headless-chrome".)
#
# spqr: this is used to compile the "SPQR script" (spqr.cpp)
#  contained in the graph_collator/ directory of MetagenomeScope.
#  NOTE that compiling the SPQR script is only necessary if you want to use
#  the -spqr option of the preprocessing script (graph_collator/collate.py).
#  See the System Requirements and Installation Instruction pages on
#  MetagenomeScope's wiki (https://github.com/marbl/MetagenomeScope/wiki)
#  for details on this option.

.PHONY: generaltest spqrtest viewertest test spqr

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
# Linux/OS X systems.
SCRIPT_DIR = graph_collator/
SPQR_CODE = $(addprefix $(SCRIPT_DIR), spqr.cpp)
SPQR_BINARY = $(addprefix $(SCRIPT_DIR), spqr)

# -B: don't create __pycache__/ directories
generaltest:
	python2.7 -B -m pytest -m "not spqrtest"
	rm graph_collator/tests/output/*

spqrtest:
	python2.7 -B -m pytest -m "spqrtest"
	rm graph_collator/tests/output/*

viewertest:
	fish minify_files.fish
	mocha-headless-chrome -f viewer/headless_tests_index.min.html

test: generaltest spqrtest viewertest

spqr:
	$(COMPILER) $(SPQR_CODE) $(CFLAGS) $(OGDF_FLAGS) -o $(SPQR_BINARY)
