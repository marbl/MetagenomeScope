# NOTE: this Makefile is a work in progress -- some of the variables should
# be changed for different systems -- see INSTALLING.txt for more info.
COMPILER = g++
# Omitting optimization and warning flags for the time being; adding those
# later would be a good idea.
CFLAGS = -std=gnu++11
OGDF_INCL = -I ~/Software/OGDF/OGDF/include/
OGDF_LINK = -L ~/Software/OGDF/OGDF/_release/ 
OGDF_FLAGS = $(OGDF_INCL) $(OGDF_LINK) -l OGDF -pthread
SCRIPT_DIR = graph_collator/
SPQR_CODE = $(addprefix $(SCRIPT_DIR), spqr.cpp)
SPQR_BINARY = $(addprefix $(SCRIPT_DIR), spqr)

# Actually compile the SPQR script
all:
	$(COMPILER) $(SPQR_CODE) $(CFLAGS) $(OGDF_FLAGS) -o $(SPQR_BINARY)
