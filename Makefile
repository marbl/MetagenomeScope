# SPQR Script Makefile
#
# This Makefile is used to compile the "SPQR script" (spqr.cpp) contained in
# the graph_collator/ directory of MetagenomeScope.
# Compiling the SPQR script is only necessary if you want to use the -spqr
# option of the preprocessing script (graph_collator/collate.py).
#
# See https://github.com/marbl/MetagenomeScope/wiki/System-Requirements and
# https://github.com/marbl/MetagenomeScope/wiki/Building-SPQR-Functionality-for-the-Preprocessing-Script
# for details on using this Makefile.

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

# Actually compile the SPQR script
all:
	$(COMPILER) $(SPQR_CODE) $(CFLAGS) $(OGDF_FLAGS) -o $(SPQR_BINARY)
