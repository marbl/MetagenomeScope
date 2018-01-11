COMPILER = g++
# Omitting optimization and warning flags for the time being; adding those
# later would be a good idea.
CFLAGS = -std=gnu++11
#
# See http://www.ogdf.net/doku.php for more information on downloading and
# installing OGDF.
#
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
