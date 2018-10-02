# Since the bulk of MetagenomeScope's code isn't compiled, this Makefile only
# performs a few actions using the following (phony) targets:
#
# test: Runs tests for the preprocessing script using pytest. All of these
#  tests should be located in the tests/ directory of MetagenomeScope.
#  (In the future, this should also be used to run JS tests.)
#
# spqr: this is used to compile the "SPQR script" (spqr.cpp)
#  contained in the graph_collator/ directory of MetagenomeScope.
#  NOTE that compiling the SPQR script is only necessary if you want to use
#  the -spqr option of the preprocessing script (graph_collator/collate.py).
#  See the System Requirements and "Building SPQR Functionality" pages on
#  MetagenomeScope's wiki (https://github.com/marbl/MetagenomeScope/wiki)
#  for details on this option.

.PHONY: test spqr

COMPILER = g++
# Omitting optimization and warning flags for the time being; adding those
# later would be a good idea.
CFLAGS = -std=gnu++11

# NOTE modify this to point to the include directory of OGDF on your system
OGDF_INCL = -I ~/Software/OGDF/OGDF/include/
# NOTE modify this to point to the _release directory of OGDF on your system
OGDF_LINK = -L ~/Software/OGDF/OGDF/_release/ 

OGDF_FLAGS = $(OGDF_INCL) $(OGDF_LINK) -l OGDF -pthread
# Apparently forward-slashes should work on Windows systems as well as
# Linux/OS X systems.
SCRIPT_DIR = graph_collator/
SPQR_CODE = $(addprefix $(SCRIPT_DIR), spqr.cpp)
SPQR_BINARY = $(addprefix $(SCRIPT_DIR), spqr)

test:
	python2.7 -m pytest

spqr:
	$(COMPILER) $(SPQR_CODE) $(CFLAGS) $(OGDF_FLAGS) -o $(SPQR_BINARY)
