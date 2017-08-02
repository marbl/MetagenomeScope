#!/usr/bin/env python
# Copyright (C) 2017 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
# 
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
####
# Converts an assembly graph (LastGraph, GFA, MetaCarvel GML) to a DOT file,
# lays out the DOT file using Graphviz, and then reconciles the layout data
# with biological data in a SQLite .db file that can be read by the
# MetagenomeScope viewer interface.
#
# For usage information, please see README.md in the root directory of
# MetagenomeScope.

# For parsing command-line arguments
import argparse
# For flushing the output
from sys import stdout
# For running the C++ spqr script binary
from subprocess import check_output, STDOUT
# For laying out graphs using Graphviz (in particular, via the dot and sfdp
# layout tools)
import pygraphviz
# For creating the output directory, and for file I/O
import os
# For parsing certain filenames easily
import re
# For calculating quartiles, etc. for edge weight outlier detection
import numpy
# For checking I/O errors
import errno
# For interfacing with SQLite
import sqlite3
# For benchmarking
import time

import graph_objects
import config

# Get argument information
parser = argparse.ArgumentParser(description=config.COLLATE_DESCRIPTION)
parser.add_argument("-i", "--inputfile", required=True,
    help="input assembly graph filename (LastGraph, GFA, or Bambus 3 GML)")
parser.add_argument("-o", "--outputprefix", required=True,
    help="output file prefix for .db and .xdot/.gv files")
parser.add_argument("-d", "--outputdirectory", required=False,
    default=os.getcwd(),
    help="directory in which all output files will be stored;" + \
        " defaults to current working directory")
parser.add_argument("-pg", "--preservegv", required=False, action="store_true",
        default=False,
        help="save all .gv (DOT) files generated for connected components")
parser.add_argument("-px", "--preservexdot", required=False, default=False,
        action="store_true",
        help="save all .xdot files generated for connected components")
parser.add_argument("-w", "--overwrite", required=False, default=False,
        action="store_true", help="overwrite output (.db/.gv/.xdot) files")
parser.add_argument("-b", "--bicomponentsfile", required=False,
    help="file containing bicomponent information for the assembly graph" + \
        " (will be generated using the SPQR script in the output directory" + \
        " if not passed)")
parser.add_argument("-au", "--assumeunoriented", required=False, default=False,
        action="store_true", help="assume that input GML-file graphs are" + \
            " unoriented (default for GML files is assuming they are" + \
            " oriented); this option is unfinished")
parser.add_argument("-ao", "--assumeoriented", required=False, default=False,
        action="store_true", help="assume that input LastGraph-/GFA-file" + \
            " graphs are oriented (default for LastGraph/GFA files is" + \
            " assuming they are unoriented); this option is unfinished")
args = parser.parse_args()
asm_fn = args.inputfile
output_fn = args.outputprefix
db_fn = output_fn + ".db"
dir_fn = args.outputdirectory
preserve_gv = args.preservegv
preserve_xdot = args.preservexdot
overwrite = args.overwrite
bicmps_fullfn = args.bicomponentsfile
assume_unoriented = args.assumeunoriented
assume_oriented = args.assumeoriented

try:
    os.makedirs(dir_fn)
except:
    if not os.path.isdir(dir_fn):
        raise IOError, dir_fn + config.EXISTS_AS_NON_DIR_ERR

# Assign flags for auxiliary file creation
if overwrite:
    flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
else:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

def check_file_existence(filepath):
    """Returns True if the given filepath does exist as a non-directory file
       and overwrite is set to True.

       Returns False if the given filepath does not exist at all.

       Raises errors if:
        -The given filepath does exist but overwrite is False
        -The given filepath exists as a directory

       Note that this has some race conditions associated with it -- the
       user or some other process could circumvent these error-checks by,
       respectively:
        -Creating a file at the filepath after this check but before opening
        -Creating a directory at the filepath after this check but before
         opening

       We get around this by using os.fdopen() wrapped to os.open() with
       certain flags (based on whether or not the user passed -w) set,
       for the one place in this script where we directly write to a file
       (in save_aux_file()). This allows us to guarantee an error will be
       thrown and no data will be erroneously written in the first two cases,
       while (for most non-race-condition cases) allowing us to display a
       detailed error message to the user here, before we even try to open the
       file.
    """
    if os.path.exists(filepath):
        basename = os.path.basename(filepath)
        if os.path.isdir(filepath):
            raise IOError, filepath + config.IS_DIR_ERR
        if not overwrite:
            raise IOError, filepath + config.EXISTS_ERR
        return True
    return False

def safe_file_remove(filepath):
    """Safely (preventing race conditions of the file already being removed)
       removes a file located at the given file path.
    """
    try:
        os.remove(filepath)
    except OSError as error:
        if error.errno == errno.ENOENT:
            # Something removed the file before we could. That's alright.
            pass
        else:
            # Something strange happened -- maybe someone changed the file
            # to a directory, or something similarly odd. Raise the original
            # error to inform the user.
            raise

# Right off the bat, check if the .db file name causes an error somehow.
# (See check_file_existence() for possible causes.)
# This prevents us from doing a lot of work and then realizing that due to the
# nature of the .db file name we can't continue.
# Yeah, there is technically a race condition here where the user/some process
# could create a file with the same .db name in between us checking for its
# existence here/etc. and us actually connecting to the .db file using SQLite.
# However, as is detailed below, that doesn't really matter -- SQLite will
# handle that condition suitably.
db_fullfn = os.path.join(dir_fn, db_fn)
if check_file_existence(db_fullfn):
    # The user asked to overwrite this database via -w, so remove it
    safe_file_remove(db_fullfn)

def dfs(n):
    """Recursively runs depth-first search, starting at node n.
       Returns a list of all nodes found that corresponds to a list of all
       nodes within the entire connected component (ignoring edge
       directionality) in which n resides.
       
       This assumes that the connected component containing n has not had this
       method run on it before (due to its reliance on the .seen_in_dfs Node
       property).

       (In identifying a connected component, the graph is treated as if
       its edges are undirected, so the actual starting node within a
       connected component should not make a difference on the connected
       component node list returned.)

       I modified this function to not use recursion since Python isn't
       super great at that -- this allows us to avoid hitting the maximum
       recursion depth, which would cause us to get a RuntimeError for
       really large connected components.
    """
    nodes_to_check = [n]
    nodes_in_ccomponent = []
    # len() of a list in python is a constant-time operation, so this is okay--
    while len(nodes_to_check) > 0:
        # We rely on the invariant that all nodes in nodes_to_check have
        # seen_in_dfs = False, and that no duplicate nodes exist within
        # nodes_to_check
        j = nodes_to_check.pop()
        j.seen_in_dfs = True
        nodes_in_ccomponent.append(j)
        tentative_nodes = j.outgoing_nodes + j.incoming_nodes
        # Only travel to unvisited and not already-marked-to-visit neighbor
        # nodes of j
        for m in tentative_nodes:
            if not m.seen_in_dfs and not m.in_nodes_to_check:
                # in_nodes_to_check prevents duplicate nodes in that list
                m.in_nodes_to_check = True
                nodes_to_check.append(m)
    return nodes_in_ccomponent

def reverse_complement(dna_string):
    """Returns the reverse complement of a string of DNA.
   
       e.g. reverse_complement("GCATATA") == "TATATGC"
   
       This is used when getting data from GFA files (which only include
       positive DNA sequence information).
       
       Note that this will break on invalid DNA input (so inputs like RNA
       or protein sequences, or sequences that contain spaces, will cause
       this to fail).
    """
    rc = ""
    dna_last_char_index = len(dna_string) - 1
    for nt in range(dna_last_char_index, -1, -1):
        rc += config.COMPLEMENT[dna_string[nt]] 
    return rc

def gc_content(dna_string):
    """Returns the GC content (as a float in the range [0, 1]) of a string of
       DNA, in a 2-tuple with the second element of the tuple being the
       actual number of Gs and Cs in the dna_string.
       
       Assumes that the string of DNA only contains nucleotides (e.g., it
       doesn't contain any spaces).

       For reference, the GC content of a DNA sequence is the percentage of
       nucleotides within the sequence that are either G (guanine) or C
       (cytosine).

       e.g. gc_content("GCATTCAC") == (0.5, 4)
    """
    # len() of a str is a constant-time operation in Python
    seq_len = len(dna_string)
    gc_ct = 0
    for nt in dna_string:
        if nt == 'G' or nt == 'C':
            gc_ct += 1
    return (float(gc_ct) / seq_len), gc_ct

def assembly_gc(gc_ct, total_bp):
    """Returns the G/C content of an assembly, where total_bp is the number of
       base pairs (2 * the number of nucleotides) and gc_ct is the number of
       G/C nucleotides in the entire assembly.
    """
    if gc_ct == None:
        return None
    else:
        return float(gc_ct) / (2 * total_bp)

def negate_node_id(id_string):
    """Negates a node ID.
    
       e.g. "-18" -> "18", "18" -> "-18"
    """
    if id_string[0] == '-':
        return id_string[1:]
    else:
        return '-' + id_string

def n50(node_lengths):
    """Determines the N50 statistic of an assembly, given its node lengths.

       Note that multiple definitions of the N50 statistic exist (see
       https://en.wikipedia.org/wiki/N50,_L50,_and_related_statistics for
       more information).
       
       Here, we use the calculation method described by Yandell and Ence,
       2012 (Nature) -- see
       http://www.nature.com/nrg/journal/v13/n5/box/nrg3174_BX1.html for a
       high-level overview.
    """

    if len(node_lengths) == 0:
        raise ValueError, config.EMPTY_LIST_N50_ERR
    sorted_lengths = sorted(node_lengths, reverse=True)
    i = 0
    running_sum = 0
    half_total_length = 0.5 * sum(sorted_lengths)
    while running_sum < half_total_length:
        if i >= len(sorted_lengths):
            # This should never happen, but just in case
            raise IndexError, config.N50_CALC_ERR
        running_sum += sorted_lengths[i]
        i += 1
    # Return length of shortest node that was used in the running sum
    return sorted_lengths[i - 1]

def save_aux_file(aux_filename, source, layout_msg_printed, warnings=True):
    """Given a filename and a source of "input" for the file, writes to that
       file (using check_file_existence() accordingly).

       If aux_filename ends with ".xdot", we assume that source is a
       pygraphviz.AGraph object of which we will write its "drawn" xdot output
       to the file.

       Otherwise, we assume that source is just a string of text to write
       to the file.

       If check_file_existence() gives us an error (or if os.open() gives
       us an error due to the flags we've used), we don't save the
       aux file in particular. The default behavior (if warnings=True) in this
       case is to print an error message accordingly (its
       formatting depends partly on whether or not a layout message for
       the current component was printed [given here as layout_msg_printed,
       a boolean variable] -- if so [i.e. layout_msg_printed is True], the
       error message here is printed on a explicit newline and followed
       by a trailing newline. Otherwise, the error message here is just printed
       with a trailing newline).
       
       However, if warnings=False and we get an error from either possible
       source (check_file_existence() or os.open()) then this will
       throw an error. Setting warnings=False should only be done for
       operations that are required to generate a .db file -- care should be
       taken to ensure that .db files aren't partially created before trying
       save_aux_file with warnings=False, since that could result in an
       incomplete .db file being generated (which might confuse users).
       If warnings=False, then the value of layout_msg_printed is not used.

       Returns True if the file was written successfully; else, returns False.
    """
    fullfn = os.path.join(dir_fn, aux_filename)
    ex = None
    try:
        ex = check_file_existence(fullfn)
        # We use the defined flags (based on whether or not -w was passed)
        # to ensure some degree of atomicity in our file operations here,
        # preventing errors whenever possible
        with os.fdopen(os.open(fullfn, flags, config.AUXMOD), 'w') as file_obj:
            if aux_filename.endswith(".xdot"):
                file_obj.write(source.draw(format="xdot"))
            else:
                file_obj.write(source)
        return True
    except (IOError, OSError) as e:
        # An IOError indicates check_file_existence failed, and (far less
        # likely, but still technically possible) an OSError indicates
        # os.open failed
        msg = config.SAVE_AUX_FAIL_MSG + "%s: %s" % (aux_filename, e)
        if not warnings:
            raise type(e), msg
        # If we're here, then warnings = True.
        # Don't save this file, but continue the script's execution.
        if layout_msg_printed:
            operation_msg("\n" + msg, newline=True)
        else:
            operation_msg(msg, newline=True)
        return False

def operation_msg(message, newline=False):
    """Prints a message (by default, no trailing newline), then flushes stdout.

       Flushing stdout helps to ensure that the user sees the message (even
       if it is followed by a long operation in this program). The trailing
       newline is intended for use with conclude_msg(), defined below.
    """
    if newline: print message
    else: print message,
    stdout.flush()

def conclude_msg(message=config.DONE_MSG):
    """Prints a message indicating that a long operation was just finished.
       
       This message will usually be appended on to the end of the previous
       printed text (due to use of operation_msg), to save vertical terminal
       space (and look a bit fancy).
    """       
    print message

# Maps Node ID (as int) to the Node object in question
# This is nice, since it allows us to do things like nodeid2obj.values()
# to get a list of every Node object that's been processed
# (And, more importantly, to reconcile edge data with prev.-seen node data)
nodeid2obj = {}

def add_node_to_stdmode_mapping(n, rc=None):
    """Adds a Node object n to nodeid2obj.
    
       If rc is defined, also adds rc to nodeid2obj.

       This checks to make sure n and rc's IDs are not already in nodeid2obj.
       If either of their IDs are already in nodeid2obj before adding them, an
       AttributeError is raised.
    """
    # Check for duplicate IDs
    if n.id_string in nodeid2obj:
        raise AttributeError, config.DUPLICATE_ID_ERR + n.id_string
    # Actually add to nodeid2obj
    nodeid2obj[n.id_string] = n
    if rc != None:
        if rc.id_string in nodeid2obj:
            raise AttributeError, config.DUPLICATE_ID_ERR + rc.id_string
        nodeid2obj[rc.id_string] = rc

# Like nodeid2obj, but for preserving references to clusters (NodeGroups)
clusterid2obj = {}

# Like nodeid2obj but for "single" Nodes, to be used in the SPQR-integrated
# graph
singlenodeid2obj = {}
# List of 2-tuples, where each 2-tuple contains two node IDs
# For GML files this will just contain all the normal connections in the graph
# For LastGraph/GFA files, though, this will contain half of the connections
# in the graph, due to no edges being "implied"
single_graph_edges = []

# Pertinent Assembly-wide information we use 
graph_filetype = ""
distinct_single_graph = True
# If DNA is given for each contig, then we can calculate GC content
# (In LastGraph files, DNA is always given; in GML files, DNA is never given;
# in GFA files, DNA is sometimes given.)
# (That being said, it's ostensibly possible to store DNA in an external FASTA
# file along with GML/GFA files that don't have DNA explicitly given -- so
# these constraints are subject to change.)
dna_given = True
total_node_count = 0
total_edge_count = 0
total_all_edge_count = 0
total_length = 0
total_gc_nt_count = 0
total_component_count = 0
total_single_component_count = 0
total_bicomponent_count = 0
# Used to determine whether or not we can scale edges by multiplicity/bundle
# size. Currently we make the following assumptions (might need to change) --
# -All LastGraph files contain edge multiplicity values
# -Some GML files contain edge bundle size values, and some do not
#   -The presence of a single edge in a GML file without a bundle size
#    attribute will result in edge_weights_available being set to False.
# -All GFA files do not contain edge multiplicity values
edge_weights_available = True
# List of all the node lengths in the assembly. Used when calculating n50.
bp_length_list = []

# Below "with" block parses the assembly file.
# Please consult the README for the most accurate list of assembly graph
# filetypes supported.
operation_msg(config.READ_FILE_MSG + "%s..." % (os.path.basename(asm_fn)))
with open(asm_fn, 'r') as assembly_file:
    # We don't really care about case in file extensions
    lowercase_asm_fn = asm_fn.lower()
    parsing_LastGraph = lowercase_asm_fn.endswith(config.LASTGRAPH_SUFFIX)
    parsing_GML       = lowercase_asm_fn.endswith(config.GRAPHML_SUFFIX)
    parsing_GFA       = lowercase_asm_fn.endswith(config.GFA_SUFFIX)
    if parsing_LastGraph:
        graph_filetype = "LastGraph"
        dna_given = True
        # TODO -- Should we account for SEQ/NR information here?
        curr_node_id = ""
        curr_node_bp = 1
        curr_node_depth = 1
        curr_node_dnafwd = None
        curr_node_dnarev = None
        curr_node_gcfwd = None
        curr_node_gcrev = None
        parsing_node = False
        parsed_fwdseq = False
        for line in assembly_file:
            if line[:4] == "NODE":
                parsing_node = True
                l = line.split()
                curr_node_id = l[1]
                curr_node_bp = int(l[2])
                # depth = $O_COV_SHORT1 / $COV_SHORT1 (bp)
                curr_node_depth = float(l[3]) / curr_node_bp
            elif line[:3] == "ARC":
                # ARC information is only stored on one line -- makes things
                # simple for us
                a = line.split()
                # Per the Velvet docs: "This one line implicitly represents
                # an arc from node A to B and another, with same
                # multiplicity, from -B to -A."
                # (http://computing.bio.cam.ac.uk/local/doc/velvet.pdf)
                id1 = a[1]
                id2 = a[2]
                nid2 = negate_node_id(id2)
                nid1 = negate_node_id(id1)
                mult = int(a[3])
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2],
                        multiplicity=mult)
                pid1 = id1[1:] if id1[0] == '-' else id1
                pid2 = id2[1:] if id2[0] == '-' else id2
                single_graph_edges.append((pid1, pid2))
                singlenodeid2obj[pid1].add_outgoing_edge(singlenodeid2obj[pid2])
                # Only add implied edge if the edge does not imply itself
                # (see issue #105 on GitHub for context)
                if not (id1 == nid2 and id2 == nid1):
                    nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1],
                            multiplicity=mult)
                    # Use total_all_edge_count to keep track of self-implying
                    # edges' impact on the assembly; is used in viewer tool
                    total_all_edge_count += 1
                total_all_edge_count += 1
                # Record this edge for graph statistics
                total_edge_count += 1
            elif parsing_node:
                # If we're in the middle of parsing a node's info and
                # the current line doesn't match either a NODE or ARC
                # declaration, then it refers to the node's DNA sequence.
                # It can either refer to the forward or reverse sequence -- in
                # LastGraph files, the forward sequence occurs first.
                if parsed_fwdseq:
                    # Parsing reverse sequence
                    curr_node_dnarev = line.strip()
                    curr_node_gcrev, gc_ct = gc_content(curr_node_dnarev)
                    total_gc_nt_count += gc_ct
                    curr_node_dnarev = None
                    # In any case, now that we've parsed both the forward and
                    # reverse sequences for the node's DNA (or ignored the
                    # sequences, if the user passed the -nodna flag), we are
                    # done getting data for this node -- so we can create new
                    # Node objects to be added to the .db file and used in the
                    # graph layout.
                    n = graph_objects.Node(curr_node_id, curr_node_bp, False,
                            depth=curr_node_depth, gc_content=curr_node_gcfwd)
                    c = graph_objects.Node('-' + curr_node_id,
                            curr_node_bp, True, depth=curr_node_depth,
                            gc_content=curr_node_gcrev)
                    add_node_to_stdmode_mapping(n, c)
                    # Create single Node object, for the SPQR-integrated graph
                    sn = graph_objects.Node(curr_node_id, curr_node_bp, False,
                            depth=curr_node_depth, gc_content=curr_node_gcfwd,
                            is_single=True)
                    singlenodeid2obj[curr_node_id] = sn
                    # Record this node for graph statistics
                    # Note that recording these statistics here ensures that
                    # only "fully complete" node definitions are recorded.
                    total_node_count += 1
                    total_length += curr_node_bp
                    bp_length_list.append(curr_node_bp)
                    bp_length_list.append(curr_node_bp)
                    # Clear temporary/marker variables for later use
                    curr_node_id = ""
                    curr_node_bp = 1
                    curr_node_dnafwd = None
                    curr_node_dnarev = None
                    curr_node_gcfwd = None
                    curr_node_gcrev = None
                    parsing_node = False
                    parsed_fwdseq = False
                else:
                    # Parsing forward sequence (It's actually offset by a
                    # number of bp, so we should probably mention that in
                    # README or even in the Javascript graph viewer)
                    parsed_fwdseq = True
                    curr_node_dnafwd = line.strip()
                    curr_node_gcfwd, gc_ct = gc_content(curr_node_dnafwd)
                    total_gc_nt_count += gc_ct
                    curr_node_dnafwd = None
    elif parsing_GML:
        graph_filetype = "GML"
        dna_given = False
        distinct_single_graph = False
        # Since GML files don't contain DNA
        total_gc_nt_count = None
        # Record state -- parsing node or parsing edge?
        # (This is kind of a lazy approach, but to be fair it's actually
        # sort of efficient)
        # We assume that each declaration occurs on its own line.
        parsing_node = False
        curr_node_id = None
        curr_node_bp = 0
        curr_node_orientation = None
        parsing_edge = False
        curr_edge_src_id = None
        curr_edge_tgt_id = None
        curr_edge_orientation = None
        curr_edge_mean = None
        curr_edge_stdev = None
        curr_edge_bundlesize = None
        for line in assembly_file:
            # Record node attributes/detect end of node declaration
            if parsing_node:
                if line.strip().startswith("id"):
                    l = line.split()
                    curr_node_id = l[1]
                if line.strip().startswith("label"):
                    l = line.split()
                    curr_node_label = l[1].strip("\"")
                    if curr_node_label.startswith("NODE_"):
                        label_parts = curr_node_label.split("_")
                        curr_node_label = "NODE_" + label_parts[1]
                elif line.strip().startswith("orientation"):
                    l = line.split()
                    curr_node_orientation = l[1] # either "FOW" or "REV"
                elif line.strip().startswith("length"):
                    # fetch value from length attribute
                    l = line.split()
                    curr_node_bp = int(l[1].strip("\""))
                elif line.strip().startswith("repeat"):
                    l = line.split()
                    curr_node_is_repeat = (l[1] == "1")
                elif line.endswith("]\n"):
                    # TODO pass the repeat value via optional arg to Node()
                    # Then store the repeat thing in db_values, modifying the
                    # corresponding database construction thing for nodes also
                    # then in the viewer application in renderNodeObject()
                    # if the node has repeat === 1 then we can assign its
                    # repeatColor as the 100% color, and else we can assign its
                    # repeatColor as the 0% color. Then adding colorization
                    # stuff should just be a function of modifying the GC
                    # content stuff
                    n = graph_objects.Node(curr_node_id, curr_node_bp,
                            (curr_node_orientation == '"REV"'),
                            label=curr_node_label)
                    add_node_to_stdmode_mapping(n)
                    # Create single Node object, for the SPQR-integrated graph
                    sn = graph_objects.Node(curr_node_id, curr_node_bp, False,
                            label=curr_node_label, is_single=True)
                    singlenodeid2obj[curr_node_id] = sn
                    # Record this node for graph statistics
                    total_node_count += 1
                    total_length += curr_node_bp
                    bp_length_list.append(curr_node_bp)
                    # Clear tmp/marker variables
                    parsing_node = False
                    curr_node_id = None
                    curr_node_bp = 0
                    curr_node_orientation = None
            elif parsing_edge:
                if line.strip().startswith("source"):
                    l = line.split()
                    curr_edge_src_id = l[1]
                elif line.strip().startswith("target"):
                    l = line.split()
                    curr_edge_tgt_id = l[1]
                elif line.strip().startswith("orientation"):
                    l = line.split()
                    curr_edge_orientation = l[1].strip('"')
                elif line.strip().startswith("bsize"):
                    l = line.split()
                    curr_edge_bundlesize = int(l[1].strip('"'))
                elif line.strip().startswith("mean"):
                    l = line.split()
                    curr_edge_mean = float(l[1].strip('"'))
                elif line.strip().startswith("stdev"):
                    l = line.split()
                    curr_edge_stdev = float(l[1].strip('"'))
                elif line.endswith("]\n"):
                    nodeid2obj[curr_edge_src_id].add_outgoing_edge(
                            nodeid2obj[curr_edge_tgt_id],
                            multiplicity=curr_edge_bundlesize,
                            orientation=curr_edge_orientation,
                            mean=curr_edge_mean,
                            stdev=curr_edge_stdev)
                    #single_graph_edges.append((curr_edge_src_id, \
                    #    curr_edge_tgt_id))
                    singlenodeid2obj[curr_edge_src_id].add_outgoing_edge(
                            singlenodeid2obj[curr_edge_tgt_id])
                    total_edge_count += 1
                    total_all_edge_count += 1
                    if curr_edge_bundlesize == None:
                        edge_weights_available = False
                    # Clear tmp/marker vars
                    parsing_edge = False
                    curr_edge_src_id = None
                    curr_edge_tgt_id = None
                    curr_edge_orientation = None
                    curr_edge_bundlesize = None
                    curr_edge_mean = None
                    curr_edge_stdev = None
            # Start parsing node
            elif line.endswith("node [\n"):
                parsing_node = True
            # Start parsing edge
            elif line.endswith("edge [\n"):
                parsing_edge = True
    elif parsing_GFA:
        graph_filetype = "GFA"
        # Assume initially that DNA is given. If we encounter any contigs where
        # DNA is not given, then set this to False.
        dna_given = True
        edge_weights_available = False
        # NOTE--
        # Currently, we only parse (S)egment and (L)ink lines in GFA files,
        # and only take into account their "required" fields (as given on the
        # GFA spec).
        # TODO--
        # We can look into parsing S+L optional fields, as well as
        # (C)ontainment and (P)ath lines (and, more
        # importantly, making use of this data in the AsmViz viewer) in the
        # future, but for now having Segment + Link data should match what we
        # have for the other two supported input assembly graph filetypes.
        curr_node_id = None
        curr_node_bp = None
        curr_node_gc = None
        curr_node_dnafwd = None
        curr_node_dnarev = None
        for line in assembly_file:
            # Parsing a segment (node) line
            if line.startswith("S"):
                # For GFA files: given a + DNA seq, its - DNA seq is the
                # reverse complement of that DNA seq.
                l = line.split()
                curr_node_id = l[1]
                if curr_node_id.startswith("NODE_"):
                    curr_node_id = curr_node_id.split("_")[1]
                elif curr_node_id.startswith("tig"):
                    curr_node_id = curr_node_id[3:]
                # The sequence data can be optionally not given -- in this
                # case, a single asterisk, *, will be located at l[2].
                curr_node_dnafwd = l[2]
                if curr_node_dnafwd != "*":
                    curr_node_bp = len(curr_node_dnafwd)
                    curr_node_dnarev = reverse_complement(curr_node_dnafwd)
                    # The G/C content of a DNA sequence "m" will always equal
                    # the G/C content of the reverse complement of m, since
                    # a reverse complement just flips A <-> T and C <-> G --
                    # meaning that the total count of C + G occurrences does
                    # not change.
                    # Hence, we just need to calculate the G/C content here
                    # once. This is not the case for LastGraph nodes, though.
                    curr_node_gc, gc_ct = gc_content(curr_node_dnafwd)
                    if dna_given:
                        # If DNA is not given for at least one contig seen thus
                        # far, don't bother updating this further. (We'll only
                        # display assembly GC content info in the viewer
                        # interface if DNA was given for all contigs, not just
                        # for some of them.)
                        total_gc_nt_count += (2 * gc_ct)
                else:
                    # Allow user to not include DNA but indicate seq length via
                    # the LN property
                    dna_given = False
                    curr_node_bp = None
                    for seq_attr in l[3:]:
                        if seq_attr.startswith("LN:i:"):
                            curr_node_bp = int(seq_attr[5:])
                            break
                    if curr_node_bp == None:
                        errmsg = config.SEQ_NOUN+curr_node_id+config.NO_DNA_ERR
                        raise AttributeError, errmsg
                curr_node_dnafwd = None
                curr_node_dnarev = None
                nPos = graph_objects.Node(curr_node_id, curr_node_bp, False,
                        gc_content=curr_node_gc)
                nNeg = graph_objects.Node('-' + curr_node_id, curr_node_bp,
                        True,gc_content=curr_node_gc)
                add_node_to_stdmode_mapping(nPos, nNeg)
                # Create single Node object, for the SPQR-integrated graph
                sn = graph_objects.Node(curr_node_id, curr_node_bp, False,
                        gc_content=curr_node_gc, is_single=True)
                singlenodeid2obj[curr_node_id] = sn
                # Update stats
                total_node_count += 1
                total_length += curr_node_bp
                bp_length_list.append(curr_node_bp)
                bp_length_list.append(curr_node_bp)
                curr_node_id = None
                curr_node_bp = None
                curr_node_gc = None
                curr_node_dnafwd = None
                curr_node_dnarev = None
            # Parsing a link (edge) line from some id1 to id2
            elif line.startswith("L"):
                a = line.split()
                id1 = a[1]
                id2 = a[3]
                if id1.startswith("NODE_"): id1 = id1.split("_")[1]
                if id2.startswith("NODE_"): id2 = id2.split("_")[1]
                if id1.startswith("tig"): id1 = id1[3:]
                if id2.startswith("tig"): id2 = id2[3:]
                single_graph_edges.append((id1, id2))
                singlenodeid2obj[id1].add_outgoing_edge(singlenodeid2obj[id2])
                id1 = id1 if a[2] != '-' else '-' + id1
                id2 = id2 if a[4] != '-' else '-' + id2
                nid2 = negate_node_id(id2)
                nid1 = negate_node_id(id1)
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2])
                # Only add implied edge if the edge does not imply itself
                # (see issue #105 on GitHub for context)
                if not (id1 == nid2 and id2 == nid1):
                    nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1])
                    total_all_edge_count += 1
                total_all_edge_count += 1
                # Update stats
                total_edge_count += 1
    else:
        raise IOError, config.FILETYPE_ERR
conclude_msg()

# TODO just a temporary measure; output the entire single graph as a .gv file
# I guess eventually we'd lay this out using pygraphviz and store the nodes'
# position data? But for debugging, etc. this is a nice feature to keep around
#with open("single.gv", "w") as sgraphfile:
#    sgraphfile.write("graph {\n")
#    for n in nodeid2obj.values():
#        if n.id_string[0] != '-':
#            sgraphfile.write("\t%s;\n" % (n.id_string))
#    for e in single_graph_edges:
#        sgraphfile.write("\t%s -- %s;\n" % (e[0], e[1]))
#    sgraphfile.write("}")

# NOTE -- at this stage, the entire assembly graph file has been parsed.
# This means that graph_filetype, total_node_count, total_edge_count,
# total_length, and bp_length_list are all finalized.

# Try to collapse special "groups" of Nodes (Bubbles, Ropes, etc.)
# As we check nodes, we add either the individual node (if it can't be
# collapsed) or its collapsed "group" (if it could be collapsed) to a list
# of nodes to draw, which will later be processed and output to the .gv file.

# We apply "precedence" here: identify all bubbles, then frayed ropes, then
# cycles, then chains. A TODO is making that precedence configurable; see #87
# (and generalizing this code to get rid of redundant stuff, maybe?)
operation_msg(config.BUBBLE_SEARCH_MSG)
nodes_to_try_collapsing = nodeid2obj.values()
nodes_to_draw = []

# Find "standard" bubbles. Our algorithm here classifies a bubble as a set of
# nodes with a starting node, a set of middle nodes, and ending node, where the
# starting node has at least two outgoing paths: all of which linearly extend
# to the ending node.
# This ignores some types of bubbles that exhibit a more complex structure --
# hence why we use the bicomponent bubble detection using the SPQR script.
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a bubble
    if n.used_in_collapsing or len(n.outgoing_nodes) <= 1:
        # If n doesn't lead to multiple nodes, it couldn't be a bubble start
        continue
    bubble_validity, member_nodes = graph_objects.Bubble.is_valid_bubble(n)
    if bubble_validity:
        # Found a bubble!
        new_bubble = graph_objects.Bubble(*member_nodes)
        nodes_to_draw.append(new_bubble)
        clusterid2obj[new_bubble.id_string] = new_bubble

conclude_msg()
# Run the SPQR script, use its output to create SPQR trees and detect complex
# bubbles
operation_msg(config.SPQR_MSG)

# Clear extraneous SPQR auxiliary files from the output directory, if present
# (see issue #191 on the GitHub page)
cfn_regex = re.compile("component_(\d+)\.info")
sfn_regex = re.compile("spqr\d+\.gml")
for fn in os.listdir(dir_fn):
    match = cfn_regex.match(fn)
    if match is not None:
        c_fullfn = os.path.join(dir_fn, fn)
        if check_file_existence(c_fullfn):
            safe_file_remove(c_fullfn)
    else:
        s_match = sfn_regex.match(fn)
        if s_match is not None:
            s_fullfn = os.path.join(dir_fn, fn)
            if check_file_existence(s_fullfn):
                safe_file_remove(s_fullfn)

# Construct links file for the single graph
# (this is unnecessary for Bambus 3 GML files, but for LastGraph/GFA files it's
# needed in order to generate the SPQR tree)
s_edges_fullfn = None
if distinct_single_graph:
    s_edges_fn = output_fn + "_single_links"
    s_edges_fn_text = ""
    for e in single_graph_edges:
        # (the other values we add are just dummy values -- they don't impact
        # the biconnected components/SPQR trees that we obtain from the script)
        line = e[0] + "\tB\t" + e[1] + "\tB\t0\t0\t0\n"
        s_edges_fn_text += line
    save_aux_file(s_edges_fn, s_edges_fn_text, False, warnings=False)
    s_edges_fullfn = os.path.join(dir_fn, s_edges_fn)

# Prepare non-single-graph _links file
# (unnecessary for the case where -b is passed and the input graph has a
# distinct single graph)
edges_fullfn = None
if bicmps_fullfn == None or not distinct_single_graph:
    edges_fn = output_fn + "_links"
    edges_fn_text = ""
    for n in nodes_to_try_collapsing:
        for e in n.outgoing_nodes:
            line = n.id_string + "\tB\t" + e.id_string + "\tB\t0\t0\t0\n"
            edges_fn_text += line
    save_aux_file(edges_fn, edges_fn_text, False, warnings=False)
    edges_fullfn = os.path.join(dir_fn, edges_fn)

# Get the location of the spqr script -- it should be in the same dir as
# collate.py, i.e. the currently running python script
#
# NOTE: Some of the spqr script's output is sent to stderr, so when we run the
# script we merge that with the output. Note that we don't really check the
# output of this, although we could if the need arises -- the main purpose
# of using check_output() here is to catch all the printed output of the
# spqr script.
#
# TODO: will need to change some script miscellany to work in non-Unix envs.
spqr_fullfn = os.path.join(os.path.dirname(os.path.realpath(__file__)),
    "spqr")
spqr_invocation = []
if bicmps_fullfn != None:
    # -b has been passed: we already have the file indicating separation pairs
    # This means we only need to call the script once, to output the SPQR tree
    if not distinct_single_graph:
        # Input file has oriented contigs (e.g. Bambus 3 GML output)
        # Call script once with -t and the normal links file
        spqr_invocation = [spqr_fullfn, "-l", edges_fullfn, "-t",
            "-d", dir_fn]
    else:
        # Input file has unoriented contigs (e.g. Velvet LastGraph output)
        # Call script once with -t and the single links file
        spqr_invocation = [spqr_fullfn, "-l", s_edges_fullfn, "-t",
            "-d", dir_fn]
else:
    # -b has not been passed: we need to call the SPQR script to generate the
    # separation pairs file
    # Detect (and remove) a file with a conflicting name, if present
    bicmps_fn = output_fn + "_bicmps"
    bicmps_fullfn = os.path.join(dir_fn, bicmps_fn)
    if check_file_existence(bicmps_fullfn):
        safe_file_remove(bicmps_fullfn)

    if not distinct_single_graph:
        # Input file has oriented contigs
        # Call script once with -s and -t, and the normal links file
        spqr_invocation = [spqr_fullfn, "-l", edges_fullfn, "-t",
            "-s", "-o", bicmps_fn, "-d", dir_fn]
    else:
        # Input files has unoriented contigs
        # Call script twice: once with -s and the normal links file, and once
        # with -t and the single links file
        spqr_invocation = [spqr_fullfn, "-l", edges_fullfn,
            "-s", "-o", bicmps_fn, "-d", dir_fn]
        spqr_invocation_2 = [spqr_fullfn, "-l", s_edges_fullfn, "-t",
            "-d", dir_fn]
        check_output(spqr_invocation_2, stderr=STDOUT)
check_output(spqr_invocation, stderr=STDOUT)

# NOTE we make the assumption that the generated component and spqr files
# aren't deleted after running the SPQR script but before they're read here.
# If they are for whatever reason, then this script will fail to recognize
# the corresponding biconnected component information (thus failing to draw
# a SPQR tree, and likely causing an error of some sort when creating the
# .db file).
#
# (As with the potential case where the separation pairs file is deleted after
# being generated but before being read, this falls under the scope of
# "silly race conditions that probably won't ever happen but are still
# ostensibly possible".)

conclude_msg()
operation_msg(config.SPQR_LAYOUT_MSG)
# Identify the component_*.info files representing the SPQR tree's composition
bicomponentid2fn = {}
for fn in os.listdir(dir_fn):
    match = cfn_regex.match(fn)
    if match is not None:
        c_fullfn = os.path.join(dir_fn, fn)
        if os.path.isfile(c_fullfn):
            bicomponentid2fn[match.group(1)] = c_fullfn

# Get info from the SPQR tree auxiliary files (component_*.info and spqr*.gml)
bicomponentid2obj = {}
metanode_id_regex = re.compile("^\d+$")
metanode_type_regex = re.compile("^[SPR]$")
edge_line_regex = re.compile("^v|r")
for cfn_id in bicomponentid2fn:
    with open(bicomponentid2fn[cfn_id], "r") as component_info_file:
        metanodeid2obj = {}
        curr_id = ""
        curr_type = ""
        curr_nodes = []
        curr_edges = []
        for line in component_info_file:
            if edge_line_regex.match(line):
                curr_edges.append(line.split())
            elif metanode_id_regex.match(line):
                if curr_id != "":
                    # save previous metanode info
                    new_metanode = graph_objects.SPQRMetaNode(cfn_id, curr_id,
                        curr_type, curr_nodes, curr_edges)
                    metanodeid2obj[curr_id] = new_metanode
                curr_id = line.strip()
                curr_type = ""
                curr_nodes = []
                curr_edges = []
            elif metanode_type_regex.match(line):
                curr_type = line.strip()
            else:
                # This line must describe a node within the metanode
                curr_nodes.append(singlenodeid2obj[line.split()[1]])
        # Save the last metanode in the file (won't be "covered" in loop above)
        new_metanode = graph_objects.SPQRMetaNode(cfn_id, curr_id, curr_type,
            curr_nodes, curr_edges)
        metanodeid2obj[curr_id] = new_metanode
    # At this point, we have all nodes in the entire SPQR tree for a
    # given biconnected component saved in metanodeid2obj.
    # For now, let's just parse the structure of this tree and lay it out using
    # GraphViz -- will implement in the web visualization tool soon.
    tree_structure_fn = os.path.join(dir_fn, "spqr%s.gml" % (cfn_id))
    # List of 2-tuples of SPQRMetaNode objects.
    with open(tree_structure_fn, "r") as spqr_structure_file:
        parsing_edge = False
        source_metanode = None
        target_metanode = None
        for line in spqr_structure_file:
            if line.strip().startswith("edge ["):
                parsing_edge = True
            elif parsing_edge:
                if line.strip().startswith("]"):
                    parsing_edge = False
                    # save edge data
                    source_metanode.add_outgoing_edge(target_metanode)
                    source_metanode = None
                    target_metanode = None
                else:
                    id_line_parts = line.strip().split()
                    if id_line_parts[0] == "source":
                        source_metanode = metanodeid2obj[id_line_parts[1]]
                    elif id_line_parts[0] == "target":
                        target_metanode = metanodeid2obj[id_line_parts[1]]
    # Determine root of the bicomponent and store it as part of the bicomponent
    curr_metanode = metanodeid2obj.values()[0] 
    while len(curr_metanode.incoming_nodes) > 0:
        # A metanode in the tree can have at most 1 parent (because that is how
        # trees work), so it's ok to just move up in the tree like so (because
        # the .incoming_node lists of SPQRMetaNode objects will always
        # have length 1)
        curr_metanode = curr_metanode.incoming_nodes[0]
    # At this point, we've obtained the full contents of the tree: both the
    # skeletons of its metanodes, and the edges between metanodes. (This data
    # is stored as attributes of the SPQRMetaNode objects in question.)
    metanode_list = metanodeid2obj.values()
    bicomponentid2obj[cfn_id] = graph_objects.Bicomponent(cfn_id, \
        metanode_list, curr_metanode)
    total_bicomponent_count += 1

# Now that the potential bubbles have been detected by the spqr script, we
# sort them in ascending order of size and then create Bubble objects
# accordingly.
conclude_msg()
operation_msg(config.BICOMPONENT_BUBBLE_SEARCH_MSG)

with open(bicmps_fullfn, "r") as potential_bubbles_file:
    bubble_lines = potential_bubbles_file.readlines()
# Sort the bubbles in ascending order of number of nodes contained.
# This can be done by counting the number of tabs, since those are the
# separators between nodes on each line: therefore, more tabs = more nodes
bubble_lines.sort(key=lambda c: c.count("\t"))
for b in bubble_lines:
    bubble_nodes = b.split()
    # The first two nodes listed on a line are the source and sink node of the
    # biconnected component; they're listed later on the line, so we ignore
    # them when actually drawing the bubble.
    bubble_line_node_ids = bubble_nodes[2:]

    # As a heuristic, we disallow complex bubbles of node size > 10. This is to
    # prevent bubbles being detected that are so complex that they "aren't
    # really bubbles."
    if len(bubble_line_node_ids) > 10:
        # We can just break here, since the bubble lines are sorted in
        # ascending order of size
        break

    # Validate this "separation pair" as a source-sink pair (i.e. an actual
    # bubble). If validation fails, move on.
    bubble_node_objects = [nodeid2obj[k] for k in bubble_nodes]
    if not graph_objects.Bubble.is_valid_source_sink_pair(bubble_node_objects):
        continue
    curr_bubble_nodeobjs = []
    for node_id in bubble_line_node_ids:
        try:
            curr_bubble_nodeobjs.append(nodeid2obj[node_id])
        except KeyError, e:
            raise KeyError, "Bicomponents file %s contains invalid node %s" % \
                (bicmps_fullfn, e)
    new_bubble = graph_objects.Bubble(*curr_bubble_nodeobjs)
    nodes_to_draw.append(new_bubble)
    clusterid2obj[new_bubble.id_string] = new_bubble

conclude_msg()
operation_msg(config.FRAYEDROPE_SEARCH_MSG)
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a rope
    if n.used_in_collapsing or len(n.outgoing_nodes) != 1:
        # If n doesn't lead to a single node, it couldn't be a rope start
        continue
    rope_validity, member_nodes = graph_objects.Rope.is_valid_rope(n)
    if rope_validity:
        # Found a frayed rope!
        new_rope = graph_objects.Rope(*member_nodes)
        nodes_to_draw.append(new_rope)
        clusterid2obj[new_rope.id_string] = new_rope

conclude_msg()
operation_msg(config.CYCLE_SEARCH_MSG)
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a cycle
    if n.used_in_collapsing:
        continue
    cycle_validity, member_nodes = graph_objects.Cycle.is_valid_cycle(n)
    if cycle_validity:
        # Found a cycle!
        new_cycle = graph_objects.Cycle(*member_nodes)
        nodes_to_draw.append(new_cycle)
        clusterid2obj[new_cycle.id_string] = new_cycle

conclude_msg()
operation_msg(config.CHAIN_SEARCH_MSG)
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a chain
    if n.used_in_collapsing or len(n.outgoing_nodes) != 1:
        # If n doesn't lead to a single node, it couldn't be a chain start
        continue
    chain_validity, member_nodes = graph_objects.Chain.is_valid_chain(n)
    if chain_validity:
        # Found a chain!
        new_chain = graph_objects.Chain(*member_nodes)
        nodes_to_draw.append(new_chain)
        clusterid2obj[new_chain.id_string] = new_chain

conclude_msg()
# Add individual (not used in collapsing) nodes to the nodes_to_draw list
# We could build this list up at the start and then gradually remove nodes as
# we use nodes in collapsing, but remove() is an O(n) operation so that'd make
# the above runtime O(4n^2) or something, so I figure just doing this here is
# generally faster.
for n in nodes_to_try_collapsing:
    if not n.used_in_collapsing:
        nodes_to_draw.append(n)

# Identify connected components in the "single" graph
# We'll need to actually run DFS if distinct_single_graph is True.
# However, if it's False, then we can just run DFS on the "double" graph to
# identify its connected components -- and then use those connected components'
# nodes' IDs to construct the single graph's connected components.
operation_msg(config.COMPONENT_MSG)
single_connected_components = []
if distinct_single_graph:
    for n in singlenodeid2obj.values():
        if not n.seen_in_ccomponent:
            # We've identified a node within an unseen connected component.
            # Run DFS to identify all nodes in its connected component.
            # (Also identify all bicomponents in the connected component)
            node_list = dfs(n)
            bicomponent_set = set()
            for m in node_list:
                m.seen_in_ccomponent = True
                bicomponent_set = bicomponent_set.union(m.parent_bicomponents)
            single_connected_components.append(
                graph_objects.Component(node_list, bicomponent_set))
            total_single_component_count += 1

# Identify connected components in the normal (non-"single") graph
# NOTE that nodes_to_draw only contains node groups and nodes that aren't in
# node groups. This allows us to run DFS on the nodes "inside" the node
# groups, preserving the groups' existence while not counting them in DFS.
connected_components = []
for n in nodes_to_draw:
    if not n.seen_in_ccomponent and not n.is_subsumed:
        # If n is actually a group of nodes: since we're representing groups
        # here as clusters, without any adjacencies themselves, we have to
        # run DFS on the nodes within the groups of nodes to discover them.
        node_list = []
        node_group_list = []
        if issubclass(type(n), graph_objects.NodeGroup):
            # n is a node group
            if n.nodes[0].seen_in_ccomponent:
                continue
            node_list = dfs(n.nodes[0])
        else:
            # It's just a normal Node, but it could certainly be connected
            # to a group of nodes (not that it really matters)
            node_list = dfs(n)

        # Now that we've ran DFS to discover all the nodes in this connected
        # component, we go through each node to identify their groups (if
        # applicable) and add those to node_group_list if the group is not
        # already on that list. (TODO, there's probably a more efficient way
        # to do this using sets/etc.)
        for m in node_list:
            m.seen_in_ccomponent = True
            if m.used_in_collapsing and m.group not in node_group_list:
                node_group_list.append(m.group)
        connected_components.append(
            graph_objects.Component(node_list, node_group_list))
        total_component_count += 1
connected_components.sort(reverse=True, key=lambda c: len(c.node_list))

# Loop through connected_components. For each cc:
#   Set edge_weights = []
#   For all nodes in the cc:
#     For all outgoing edges of the node:
#       Append the edge's multiplicity to edge_weights
#   Get min_mult = min(edge_weights), max_mult = max(edge_weights)
#   For all nodes in the cc, again:  
#     For all outgoing edges of the node:
#       Scale the edge's thickness relative to min/max mult (see xdot2cy.js)
# ... later we'll do IQR stuff (using numpy.percentile(), maybe?)

if not distinct_single_graph:
    # Get single_connected_components from connected_components
    for c in connected_components:
        single_node_list = []
        bicomponent_set = set()
        for n in c.node_list:
            s = singlenodeid2obj[n.id_string]
            single_node_list.append(s)
            bicomponent_set = bicomponent_set.union(s.parent_bicomponents)
        single_connected_components.append(
            graph_objects.Component(single_node_list, bicomponent_set))
        total_single_component_count += 1

# At this point, we have single_connected_components ready. We're now able to
# iterate through it and lay out each connected component, with biconnected
# components replaced with solid rectangles.
single_connected_components.sort(reverse=True, key=lambda c: len(c.node_list))

conclude_msg()
# Scale "non-outlier" edges relatively. We use "Tukey fences" to identify
# outlier edge weights (see issue #184 on GitHub for context on this).
if edge_weights_available:
    operation_msg(config.EDGE_SCALING_MSG)
    for c in connected_components:
        edge_weights = []
        for n in c.node_list:
            for e in n.outgoing_edge_objects.values():
                edge_weights.append(e.multiplicity)
        # At this point, we have a list of every edge weight contained within
        # this connected component.
        non_outlier_edges = []
        non_outlier_edge_weights = []
        # (If there are < 4 edges in this connected component, don't bother
        # with flagging outliers -- at that point, computing quartiles becomes
        # a bit silly)
        if len(edge_weights) >= 4:
            # Now, calculate lower and upper Tukey fences.
            # First, calculate lower and upper quartiles (aka the
            # 25th and 75th percentiles)
            lq, uq = numpy.percentile(edge_weights, [25, 75])
            # Then, determine 1.5 * the interquartile range
            # (we can use other values than 1.5 if desired -- not set in stone)
            d = 1.5 * (uq - lq)
            # Now we can calculate the actual Tukey fences:
            lf = lq - d
            uf = uq + d
            # Now, iterate through every edge again and flag outliers.
            # Non-outlier edges will be added to a list of edges that we will
            # scale relatively
            for n in c.node_list:
                for e in n.outgoing_edge_objects.values():
                    if e.multiplicity > uf:
                        e.is_outlier = 1
                        e.thickness = 1
                    elif e.multiplicity < lf:
                        e.is_outlier = -1
                        e.thickness = 0
                    else:
                        non_outlier_edges.append(e)
                        non_outlier_edge_weights.append(e.multiplicity)
        else:
            for n in c.node_list:
                for e in n.outgoing_edge_objects.values():
                    non_outlier_edges.append(e)
                    non_outlier_edge_weights.append(e.multiplicity)
        # Perform relative scaling for non_outlier_edges
        # (Assuming, of course, that we have at least 2 non_outlier_edges)
        if len(non_outlier_edges) >= 2:
            min_ew = min(non_outlier_edge_weights)
            max_ew = max(non_outlier_edge_weights)
            if min_ew == max_ew:
                # All the outliers have the same value: we don't need to bother
                # with scaling the non-outliers
                continue
            ew_range = float(max_ew - min_ew)
            for e in non_outlier_edges:
                e.thickness = (e.multiplicity - min_ew) / ew_range
    conclude_msg()

operation_msg(config.DB_INIT_MSG + "%s..." % (db_fn))
# Now that we've done all our processing on the assembly graph, we create the
# output file: a SQLite database in which we store biological and graph layout
# information. This will be opened in the Javascript graph viewer.
#
# Note that there's technically a race condition here, but SQLite handles
# itself so well that we don't need to bother catching it. If, somehow, a
# file with the name db_fullfn is created in between when we run
# check_file_existence(db_fullfn) and sqlite3.connect(db_fullfn), then that
# file will either:
# -Be repurposed as a database containing this data in addition to
#  its original data (if the file is a SQLite database, but stores other
#  data -- expected behavior for this case)
# -Cause the first cursor.execute() call to fail since the database already
#  has a nodes table (if the file is a SQLite database this program has
#  generated -- expected behavior for this case)
# -Cause the first cursor.execute() call to fail since the file is not a
#  SQLite database (expected behavior for this case)
# Essentially, we're okay here -- SQLite will handle the race condition
# properly, should one arise. (I doubt that race conditions will happen
# here, but I suppose you can't be too safe.)
connection = sqlite3.connect(db_fullfn)
cursor = connection.cursor()
# Define statements used for inserting a value into these tables
# The number of question marks has to match the number of table columns
NODE_INSERTION_STMT = "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
EDGE_INSERTION_STMT = "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
CLUSTER_INSERTION_STMT = "INSERT INTO clusters VALUES (?,?,?,?,?,?,?)"
COMPONENT_INSERTION_STMT = "INSERT INTO components VALUES (?,?,?,?,?,?)"
ASSEMBLY_INSERTION_STMT = \
    "INSERT INTO assembly VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
SINGLENODE_INSERTION_STMT = \
    "INSERT INTO singlenodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
SINGLEEDGE_INSERTION_STMT = "INSERT INTO singleedges VALUES (?,?,?,?,?)"
BICOMPONENT_INSERTION_STMT = \
    "INSERT INTO bicomponents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
METANODE_INSERTION_STMT = \
    "INSERT INTO metanodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
METANODEEDGE_INSERTION_STMT = "INSERT INTO metanodeedges VALUES (?,?,?,?,?,?)"
SINGLECOMPONENT_INSERTION_STMT = \
    "INSERT INTO singlecomponents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
cursor.execute("""CREATE TABLE nodes
        (id text, label text, length integer, gc_content real, depth real,
        component_rank integer, x real, y real, w real, h real,
        shape text, parent_cluster_id text)""")
cursor.execute("""CREATE TABLE edges
        (source_id text, target_id text, multiplicity integer, thickness real,
        is_outlier integer, orientation text, mean real, stdev real,
        component_rank integer, control_point_string text,
        control_point_count integer, parent_cluster_id text)""") 
cursor.execute("""CREATE TABLE clusters (cluster_id text, length integer,
        component_rank integer, left real, bottom real, right real,
        top real)""")
cursor.execute("""CREATE TABLE components
        (size_rank integer, node_count integer, edge_count integer,
        total_length integer, boundingbox_x real, boundingbox_y real)""")
cursor.execute("""CREATE TABLE assembly
        (filename text, filetype text, node_count integer,
        edge_count integer, all_edge_count integer, component_count integer,
        bicomponent_count integer, single_component_count integer,
        total_length integer, n50 integer, gc_content real,
        dna_given integer)""")
# SPQR view tables
cursor.execute("""CREATE TABLE singlenodes
        (id text, label text, length integer, gc_content real, depth real,
        scc_rank integer, x real, y real, i_x real, i_y real, w real, h real,
        parent_metanode_id text, parent_bicomponent_id text)""")
cursor.execute("""CREATE TABLE singleedges
        (source_id text, target_id text, scc_rank integer,
        parent_metanode_id text, is_virtual integer)""")
cursor.execute("""CREATE TABLE bicomponents
        (id_num integer, root_metanode_id string, scc_rank integer,
        node_count integer, left real, bottom real, right real, top real,
        i_left real, i_bottom real, i_right real, i_top real)""")
cursor.execute("""CREATE TABLE metanodes
        (metanode_id text, scc_rank integer, parent_bicomponent_id_num integer,
        descendant_metanode_count integer, node_count integer,
        total_length integer, left real, bottom real, right real,
        top real, i_left real, i_bottom real, i_right real, i_top real)""")
cursor.execute("""CREATE TABLE metanodeedges
        (source_metanode_id text, target_metanode_id text, scc_rank integer,
        control_point_string text, control_point_count integer,
        parent_bicomponent_id_num integer)""")
cursor.execute("""CREATE TABLE singlecomponents
        (size_rank integer, ex_uncompressed_node_count integer,
        ex_uncompressed_edge_count integer, im_uncompressed_node_count integer,
        im_uncompressed_edge_count integer, compressed_node_count integer,
        compressed_edge_count integer, bicomponent_count integer,
        boundingbox_x real, boundingbox_y real, i_boundingbox_x real,
        i_boundingbox_y real)""")
connection.commit()

# Insert general assembly information into the database
asm_gc = None
dna_given_val = 0
if dna_given:
    asm_gc = assembly_gc(total_gc_nt_count, total_length)
    dna_given_val = 1
graphVals = (os.path.basename(asm_fn), graph_filetype, total_node_count,
            total_edge_count, total_all_edge_count, total_component_count,
            total_bicomponent_count, total_single_component_count,
            total_length, n50(bp_length_list), asm_gc, dna_given_val)
cursor.execute(ASSEMBLY_INSERTION_STMT, graphVals)    
conclude_msg()

operation_msg(config.SPQRVIEW_LAYOUT_MSG)

# Layout both the implicit and explicit SPQR tree views
# NOTE that the order matters, since things are written to the database after
# laying out the explicit mode but not after laying out the implicit mode
# (that's done because many rows in the database are used for both layouts)

# list of all the (right, top) coords of the bounding boxes of each implicit
# single connected component
implicit_spqr_bounding_boxes = []
# lists of uncompressed node counts and of uncompressed edge counts for each
# implicit single connected component (see #223 on GitHub)
implicit_spqr_node_counts = []
implicit_spqr_edge_counts = []
for mode in ("implicit", "explicit"):
    t1 = time.time()
    single_component_size_rank = 1
    for scc in single_connected_components:
        # Layout this "single" connected component of the SPQR view
        # TODO send operation_msgs per connected component, instead of just
        # using the single "SPQRVIEW_LAYOUT_MSG"
        # Lay out each Bicomponent in this component
        # (this also lays out its child metanodes, if we're in explicit mode)
        for bicomp in scc.node_group_list:
            if mode == "explicit":
                bicomp.explicit_layout_isolated()
            else:
                bicomp.implicit_layout_isolated()
        scc_prefix = "%s_%s_spqrview_%d" % (output_fn, mode, \
                single_component_size_rank)
        gv_input = ""
        gv_input += "graph single_ccomp {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        gv_input += "\tsmoothing=\"triangle\";\n"
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        # In the layout of this single connected component, include:
        # -rectangle nodes representing each bicomponent (will be backfilled)
        # -nodes that aren't present in any biconnected components
        # -edges that are not "in" any biconnected components (includes edges
        # incident on biconnected components)
    
        # Keep track of counts of singlenodes and singleedges that are
        # specifically contained within either the root metanodes of the graph,
        # or outside of any bicomponents. Since these nodes and edges are
        # going to be drawn when the SPQR view is initially rendered, we need
        # to know these counts so we can update the progress bar accordingly.
        sc_compressed_node_count = 0
        sc_compressed_edge_count = 0
        sc_bicomponent_count = len(scc.node_group_list)
        for bicomp in scc.node_group_list:
            if mode == "implicit":
                gv_input += bicomp.implicit_backfill_node_info()
            else:
                gv_input += bicomp.node_info()
            sc_compressed_node_count +=len(bicomp.root_metanode.nodes)
            sc_compressed_edge_count +=len(bicomp.root_metanode.internal_edges)
        for m in scc.node_list:
            # Get node info for nodes not present in any bicomponents
            # Also get edge info for edges "external" to bicomponents
            if len(m.parent_bicomponents) == 0:
                gv_input += m.node_info()
                sc_compressed_node_count += 1
                # We know m is not in a bicomponent. Get its "outgoing" edge
                # info.
                for n in m.outgoing_nodes:
                    if len(n.parent_bicomponents) == 0:
                        # This edge is between two nodes, neither of which
                        # is in a bicomponent. We can lay this edge out.
                        gv_input += "\t%s -- %s;\n" % \
                                (m.id_string, n.id_string)
                        sc_compressed_edge_count += 1
                    else:
                        # m is not in a bicomponent, but n is. Lay out edges
                        # between m and all of the parent bicomponents of n.
                        for b in n.parent_bicomponents:
                            gv_input += "\t%s -- cluster_%s;\n" % \
                                    (m.id_string, b.id_string)
                            sc_compressed_edge_count += 1
            else:
                # We know m is in at least one bicomponent.
                # Get its "outgoing" edge info (in case there are edges
                # incident on m from outside one of its parent bicomponents)
                for n in m.outgoing_nodes:
                    if len(n.parent_bicomponents) == 0:
                        # m is in a bicomponent, but n is not. Lay out edges
                        # between n and all of the parent bicomponents of m.
                        for b in m.parent_bicomponents:
                            gv_input += "\tcluster_%s -- %s;\n" % \
                                    (b.id_string, n.id_string)
                            sc_compressed_edge_count += 1
                    else:
                        # Both nodes are in at least one bicomponent.
                        if len(m.parent_bicomponents.intersection( \
                                n.parent_bicomponents)) > 0:
                            # Since these two nodes share at least one
                            # bicomponent, the edge between them must be
                            # present within a bicomponent. Therefore
                            # rendering that edge would be redundant.
                            continue
                        else:
                            # Although both nodes are in >= 1 bicmps,
                            # they're in different bicomponents
                            # (this is entirely possible; consider the case
                            # where two 4-node "bubbles" in an undirected
                            # graph are joined by a single edge between
                            # two of their nodes).
                            # Thus, this edge info is not present in either
                            # set of bicomponents. So we should lay out
                            # edge(s) between the parent bicomponents of m
                            # and n.
                            for b1 in m.parent_bicomponents:
                                for b2 in n.parent_bicomponents:
                                    gv_input += \
                                            "\tcluster_%s -- cluster_%s;\n" % \
                                            (b1.id_string, b2.id_string)
                                    sc_compressed_edge_count += 1
        gv_input += "}"
        #if len(sc.node_group_list) == 0 and sc_compressed_edge_count == 0 \
        #    and len(sc.node_list) == 1:
        #        # TODO verify this is actually correct
        #        # TODO figure out sc bounding box dimensions
        #        # TODO position the single node properly
        #        # TODO then continue on?? actually idk
        #        # (as a tmp measure we could totally just continue/break here)
        h = pygraphviz.AGraph(gv_input)
        # save the .gv file if the user requested .gv preservation
        # NOTE the error messages from if these cannot be saved might be very
        # slightly improperly formatted wonky (i.e. may contain an extra
        # newline or so) because we don't handle that very in-depth here,
        # unlike in the standard mode layout loop below. 
        # Will fix that later. (see TODO above)
        if preserve_gv:
            save_aux_file(scc_prefix + ".gv", gv_input, True)
        # lay out the graph (singlenodes and singleedges outside of
        # bicomponents, and bicomponent general structures)
        h.layout(prog='sfdp')
        #h.draw(scc_prefix + ".png")
        # save the .xdot file if the user requested .xdot preservation
        if preserve_xdot:
            save_aux_file(scc_prefix + ".xdot", h, True)
    
        sc_node_count = 0
        sc_edge_count = 0
        # Retrieve layout information and use it to populate the .db file with
        # the necessary information to render the SPQR-integrated graph view
        # will be the bounding box of this single connected component's graph
        bounding_box_right = 0
        bounding_box_top = 0
        # Record layout info of nodes (incl. temporarily-"empty" Bicomponents)
        for n in h.nodes():
            try:
                curr_node = singlenodeid2obj[str(n)]
                # Since we didn't just get a KeyError, curr_node must be a
                # single node that was just laid out (and not a Bicomponent).
                # So we can process its position, width, etc. info accordingly.
                posns = tuple(float(c) for c in n.attr[u'pos'].split(','))
                exx = exy = None
                if mode == "explicit":
                    curr_node.xdot_x, curr_node.xdot_y = posns
                    exx = curr_node.xdot_x
                    exy = curr_node.xdot_y
                else:
                    curr_node.xdot_ix, curr_node.xdot_iy = posns
                    curr_node.xdot_width = float(n.attr[u'width'])
                    curr_node.xdot_height = float(n.attr[u'height'])
                    exx = curr_node.xdot_ix
                    exy = curr_node.xdot_iy
                # Try to expand the component bounding box
                right_side = exx + \
                    (config.POINTS_PER_INCH * (curr_node.xdot_width/2.0))
                top_side = exy + \
                    (config.POINTS_PER_INCH * (curr_node.xdot_height/2.0))
                if right_side > bounding_box_right: bounding_box_right = \
                        right_side
                if top_side > bounding_box_top: bounding_box_top = top_side
                # Save this single node in the .db
                sc_node_count += 1
                if mode == "explicit":
                    curr_node.set_component_rank(single_component_size_rank)
                    cursor.execute(SINGLENODE_INSERTION_STMT,
                            curr_node.s_db_values())
            except KeyError: # arising from singlenodeid2obj[a bicomponent id]
                # We use [9:] to slice off the "cluster_I" prefix on every
                # bicomponent node here
                curr_cluster = bicomponentid2obj[str(n)[9:]]
                ep = n.attr[u'pos'].split(',')
                # NOTE for anyone who's reading this: So, my code assigned the
                # .xdot_width and .xdot_height property to all NodeGroups while
                # it was parsing their layout. It's done this for a while. I
                # just realized now, though, that this is really silly, since
                # those properties (in the context of NodeGroups) are never
                # used for anything except calculating half_width_pts and
                # half_height_pts. I've modified the SPQR layout loop to not
                # store this as a class attribute; modifying the std. mode
                # layout loop below might be a good idea, also.
                if mode == "explicit":
                    curr_cluster.xdot_x = float(ep[0])
                    curr_cluster.xdot_y = float(ep[1])
                    xdot_width = float(n.attr[u'width'])
                    xdot_height = float(n.attr[u'height'])
                else:
                    curr_cluster.xdot_ix = float(ep[0])
                    curr_cluster.xdot_iy = float(ep[1])
                    xdot_width = float(n.attr[u'width'])
                    xdot_height = float(n.attr[u'height'])
                half_width_pts = \
                    (config.POINTS_PER_INCH * (xdot_width/2.0))
                half_height_pts = \
                    (config.POINTS_PER_INCH * (xdot_height/2.0))
                exr = ext = None
                if mode == "explicit":
                    curr_cluster.xdot_left = \
                            curr_cluster.xdot_x - half_width_pts
                    curr_cluster.xdot_right = \
                            curr_cluster.xdot_x + half_width_pts
                    curr_cluster.xdot_bottom =  \
                            curr_cluster.xdot_y - half_height_pts
                    curr_cluster.xdot_top = \
                            curr_cluster.xdot_y + half_height_pts
                    exr = curr_cluster.xdot_right
                    ext = curr_cluster.xdot_top
                else:
                    curr_cluster.xdot_ileft = \
                            curr_cluster.xdot_ix - half_width_pts
                    curr_cluster.xdot_iright = \
                            curr_cluster.xdot_ix + half_width_pts
                    curr_cluster.xdot_ibottom =  \
                            curr_cluster.xdot_iy - half_height_pts
                    curr_cluster.xdot_itop = \
                            curr_cluster.xdot_iy + half_height_pts
                    exr = curr_cluster.xdot_iright
                    ext = curr_cluster.xdot_itop
                # Try to expand the component bounding box
                if exr > bounding_box_right:
                    bounding_box_right = exr
                if ext > bounding_box_top:
                    bounding_box_top = ext
                # Reconcile metanodes in this bicomponent
                # No need to attempt to expand the component bounding box here,
                # since we know that all children of the bicomponent must fit
                # inside the bicomponent's area
                if mode == "implicit":
                    sc_node_count += len(curr_cluster.snid2obj)
                    sc_edge_count += len(curr_cluster.real_edges)
                    # compute positions of metanodes relative to child nodes
                    for mn in curr_cluster.metanode_list:
                        mn.assign_implicit_spqr_borders()
                    continue
                for mn in curr_cluster.metanode_list:
                    mn.xdot_x = curr_cluster.xdot_left + mn.xdot_rel_x
                    mn.xdot_y = curr_cluster.xdot_bottom + mn.xdot_rel_y
                    mn_hw_pts =(config.POINTS_PER_INCH * (mn.xdot_width / 2.0))
                    mn_hh_pts=(config.POINTS_PER_INCH * (mn.xdot_height / 2.0))
                    mn.xdot_left = mn.xdot_x - mn_hw_pts
                    mn.xdot_right = mn.xdot_x + mn_hw_pts
                    mn.xdot_bottom = mn.xdot_y - mn_hh_pts
                    mn.xdot_top = mn.xdot_y + mn_hh_pts
                    mn.xdot_ileft += curr_cluster.xdot_ileft
                    mn.xdot_iright += curr_cluster.xdot_ileft
                    mn.xdot_itop += curr_cluster.xdot_ibottom
                    mn.xdot_ibottom += curr_cluster.xdot_ibottom
                    mn.set_component_rank(single_component_size_rank)
                    cursor.execute(METANODE_INSERTION_STMT, mn.db_values())
                    # Add nodes in this metanode (...in this bicomponent) to
                    # the .db file. I'm a bit miffed that "double backfilling"
                    # is the fanciest name I can come up with for this process
                    # now.
                    for sn in mn.nodes:
                        # Node.s_db_values() uses the parent metanode
                        # information to set the position of the node in
                        # question.
                        # This is done this way because the "same" node can
                        # be in
                        # multiple metanodes in a SPQR tree, and -- even
                        # crazier, I know -- the same node can be in multiple
                        # bicomponents.
                        sc_node_count += 1
                        sn.set_component_rank(single_component_size_rank)
                        cursor.execute(SINGLENODE_INSERTION_STMT,
                                sn.s_db_values(mn))
                    # Add edges between nodes within this metanode's skeleton
                    # to the .db file. We just treat these edges as straight
                    # lines in
                    # the viewer, so we don't bother saving their layout info.
                    for se in mn.edges:
                        se.xdot_ctrl_pt_str = se.xdot_ctrl_pt_count = None
                        # Save this edge in the .db
                        sc_edge_count += 1
                        se.component_size_rank = single_component_size_rank
                        cursor.execute(SINGLEEDGE_INSERTION_STMT, \
                                se.s_db_values())
                # Reconcile edges between metanodes in this bicomponent
                for e in curr_cluster.edges:
                    # Adjust the control points to be relative to the entire
                    # component. Also, try to expand to the component
                    # bounding box.
                    p = 0
                    coord_list = \
                            [float(c) for c in e.xdot_rel_ctrl_pt_str.split()]
                    e.xdot_ctrl_pt_str = ""
                    while p <= len(coord_list) - 2:
                        if p > 0:
                            e.xdot_ctrl_pt_str += " "
                        xp = coord_list[p]
                        yp = coord_list[p + 1]
                        e.xdot_ctrl_pt_str +=str(curr_cluster.xdot_left + xp)
                        e.xdot_ctrl_pt_str +=" "
                        e.xdot_ctrl_pt_str +=str(curr_cluster.xdot_bottom + yp)
                        # Try to expand the component bounding box -- interior
                        # edges should normally be entirely within the
                        # bounding box of their node group, but some might have
                        # interior edges that go outside of the node group's
                        # bounding box
                        if xp > bounding_box_right: bounding_box_right = xp
                        if yp > bounding_box_top: bounding_box_top = yp
                        p += 2
                    # Save this edge in the .db
                    sc_edge_count += 1
                    cursor.execute(METANODEEDGE_INSERTION_STMT,
                            e.metanode_edge_db_values())
                # Save this bicomponent's information in the .db
                curr_cluster.component_size_rank = single_component_size_rank
                cursor.execute(BICOMPONENT_INSERTION_STMT, \
                        curr_cluster.db_values())
        # We don't need to get edge info or store anything in the .db just yet,
        # so just move on to the next single connected component.
        # We'll populate the .db file during the explicit layout process.
        if mode == "implicit":
            implicit_spqr_bounding_boxes.append((bounding_box_right,
                bounding_box_top))
            # Account for edges not in any bicomponents
            sc_edge_count += len(h.edges())
            implicit_spqr_node_counts.append(sc_node_count)
            implicit_spqr_edge_counts.append(sc_edge_count)
            single_component_size_rank += 1
            continue
        # Record layout info of edges that aren't inside any bicomponents.
        # Due to the possible construction of duplicates of these edges,
        # we don't actually create Edge objects for these particular edges.
        # So we have to fill in the single edge insertion statement ourselves
        # (I guess we could just declare Edge objects right here, but that'd
        # be kind of silly)
        for e in h.edges():
            source_id = e[0]
            target_id = e[1]
            # slice off the "cluster_" prefix if this edge is incident on one
            # or more biconnected components
            # (this'll save space in the database, and it'll make
            # interpreting this edge in the viewer application easier)
            if source_id.startswith("cluster_"):
                source_id = source_id[8:]
            if target_id.startswith("cluster_"):
                target_id = target_id[8:]
            xdot_ctrl_pt_str, coord_list, xdot_ctrl_pt_count = \
                graph_objects.Edge.get_control_points(e.attr[u'pos'])
            # Try to expand the component bounding box (just to be safe)
            p = 0
            while p <= len(coord_list) - 2:
                x_coord = coord_list[p]
                y_coord = coord_list[p + 1]
                if x_coord > bounding_box_right: bounding_box_right = x_coord
                if y_coord > bounding_box_top: bounding_box_top = y_coord
                p += 2
            # Save this edge in the .db
            # NOTE -- as of now we don't bother rendering this edge's
            # sfdp-determined control points in the viewer interface, since
            # most of these edges end up being normal straight lines/bezier
            # curves
            # anyway. If we decide to change this behavior to display these
            # edges with control point info, then we can modify
            # SINGLEEDGE_INSERTION_STMT above (as well as the database schema
            # for the singleedges table) to store this data accordingly.
            # (At this point, we've already computed xdot_ctrl_pt_str and
            # xdot_ctrl_pt_count, so all that would really remain is storing
            # that info in the database and handling it properly in the
            # viewer interface.)
            db_values = (source_id, target_id, single_component_size_rank,
                    None, 0)
            sc_edge_count += 1
            cursor.execute(SINGLEEDGE_INSERTION_STMT, db_values)
        # Output component information to the database
        cursor.execute(SINGLECOMPONENT_INSERTION_STMT,
            (single_component_size_rank, sc_node_count, sc_edge_count,
                implicit_spqr_node_counts[single_component_size_rank - 1],
                implicit_spqr_edge_counts[single_component_size_rank - 1],
                sc_compressed_node_count, sc_compressed_edge_count,
                sc_bicomponent_count, bounding_box_right, bounding_box_top,
                implicit_spqr_bounding_boxes[single_component_size_rank-1][0],
                implicit_spqr_bounding_boxes[single_component_size_rank-1][1]))
    
        h.clear()
        h.close()
        single_component_size_rank += 1
    t2 = time.time()
    if mode == "implicit": print "\n",
    print "SPQR %s view layout time:" % (mode),
    print "%g seconds" % (t2 - t1)

conclude_msg()
# Conclusion of script: Output (desired) components of nodes to the .gv file
t3 = time.time()
component_size_rank = 1 # largest component is 1, the 2nd largest is 2, etc
no_print = False # used to reduce excess printing (see issue #133 on GitHub)
# used in a silly corner case in which we 1) trigger the small component
# message below and 2) the first "small" component has aux file(s) that cannot
# be saved.
first_small_component = False 
for component in connected_components[:config.MAX_COMPONENTS]:
    # Since the component list is in descending order, if the current
    # component has less than config.MIN_COMPONENT_SIZE nodes then we're
    # done with displaying components
    component_node_ct = len(component.node_list)
    if component_node_ct < config.MIN_COMPONENT_SIZE:
        break
    first_small_component = False
    if not no_print:
        if component_node_ct < 5:
            # The current component is included in the small component count
            small_component_ct= total_component_count - component_size_rank + 1
            if small_component_ct > 1:
                no_print = True
                first_small_component = True
                operation_msg(config.LAYOUT_MSG + \
                    "%d " % (small_component_ct) + config.SMALL_COMPONENTS_MSG)
            # If only one small component is left, just treat it as a normal
            # component: there's no point pointing it out as a small component
        if not no_print:
            operation_msg(config.START_LAYOUT_MSG + "%d (%d nodes)..." % \
                (component_size_rank, component_node_ct))

    # Lay out all clusters individually, to be backfilled
    for ng in component.node_group_list:
        ng.layout_isolated()
    # OK, we're displaying this component.
    # Get the node info (for both normal nodes and clusters), and the edge
    # info (obtained by just getting the outgoing edge list for each normal
    # node in the component). This is an obviously limited subset of the
    # data we've ascertained from the file; once we parse the layout
    # information (.xdot) generated by GraphViz, we'll reconcile that data
    # with the previously-stored biological data.
    node_info, edge_info = component.node_and_edge_info()
    component_prefix = "%s_%d" % (output_fn, component_size_rank)
    # NOTE: Currently, we reduce each component of the asm. graph to a DOT
    # string that we send to pygraphviz. However, we could also send
    # nodes/edges procedurally, using add_edge(), add_node(), etc.
    # That might be faster, and it might be worth doing;
    # however, for now I think this approach should be fine (knock on wood).
    gv_input = ""
    gv_input += "digraph asm {\n"
    if config.GRAPH_STYLE != "":
        gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
    if config.GLOBALNODE_STYLE != "":
        gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
    if config.GLOBALEDGE_STYLE != "":
        gv_input += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)
    gv_input += node_info
    gv_input += edge_info
    gv_input += "}"
    h = pygraphviz.AGraph(gv_input)
    # save the .gv file if the user requested .gv preservation
    layout_msg_printed = (not no_print) or first_small_component
    # We use "r" to determine whether or not to print a newline before the
    # .xdot file error message, if we would print an error message there
    r = True
    if preserve_gv:
        r=save_aux_file(component_prefix + ".gv", gv_input, layout_msg_printed)

    # lay out the graph in .xdot -- this step is the main bottleneck in the
    # python side of AsmViz
    # NOTE if dot is taking a really long time to lay stuff out, then other
    # Graphviz layout programs (e.g. sfdp) can be used instead -- however
    # they'll generally produce less useful drawings for directed graphs
    h.layout(prog='dot')
    # save the .xdot file if the user requested .xdot preservation
    if preserve_xdot:
        # AGraph.draw() doesn't perform graph positioning if layout()
        # has already been called on the given AGraph and no prog is
        # specified -- so this should be relatively fast
        if not r:
            layout_msg_printed = False
        save_aux_file(component_prefix + ".xdot", h, layout_msg_printed)

    # Record the layout information of the graph's nodes, edges, and clusters

    # various stats we build up about the current component as we parse layout
    component_node_count   = 0
    component_edge_count   = 0
    component_total_length = 0
    # We use the term "bounding box" here, where "bounding box" refers to
    # just the (x, y) coord of the rightmost & topmost point in the graph:
    # (0, 0) is always the bottom left corner of the total bounding box
    # (although I have seen some negative "origin" points, which is confusing
    # and might contribute to a loss of accuracy for iterative drawing -- see
    # #148 for further information).
    #
    # So: we don't need the bounding box for positioning the entire graph.
    # However, we do use it for positioning clusters/nodes individually when we
    # "iteratively" draw the graph -- without an accurate bounding box, the
    # iterative drawing is going to look weird if clusters aren't positioned
    # "frequently" throughout the graph. (See #28 for reference.)
    #
    # We can't reliably access h.graph_attr due to a bug in pygraphviz.
    # See https://github.com/pygraphviz/pygraphviz/issues/113 for context.
    # If we could access the bounding box, here's how we'd do it --
    #bb = h.graph_attr[u'bb'].split(',')[2:]
    #bounding_box = [float(c) for c in bb]
    # 
    # So, then, we obtain the bounding box "approximately," by finding the
    # right-most and top-most coordinates within the graph from:
    # -Cluster bounding boxes (which we can access fine, for some reason.)
    # -Node boundaries (we use some math to determine the actual borders of
    #  nodes, since node position refers to the center of the node)
    # -Edge control points -- note that this may cause something of a loss in
    #  precision if we convert edge control points in Cytoscape.js in a way
    #  that changes the edge structure significantly
    bounding_box_right = 0
    bounding_box_top = 0

    # Record layout info of nodes (incl. rectangular "empty" node groups)
    for n in h.nodes():
        try:
            curr_node = nodeid2obj[str(n)]
            component_node_count += 1
            component_total_length += curr_node.bp
            if curr_node.group != None:
                continue
            ep = n.attr[u'pos'].split(',')
            curr_node.xdot_x, curr_node.xdot_y = tuple(float(c) for c in ep)
            curr_node.xdot_width = float(n.attr[u'width'])
            curr_node.xdot_height = float(n.attr[u'height'])
            # Try to expand the component bounding box
            right_side = curr_node.xdot_x + \
                (config.POINTS_PER_INCH * (curr_node.xdot_width/2.0))
            top_side = curr_node.xdot_y + \
                (config.POINTS_PER_INCH * (curr_node.xdot_height/2.0))
            if right_side > bounding_box_right: bounding_box_right = right_side
            if top_side > bounding_box_top: bounding_box_top = top_side
            # Save this cluster in the .db
            curr_node.xdot_shape = str(n.attr[u'shape'])
            curr_node.set_component_rank(component_size_rank)
            cursor.execute(NODE_INSERTION_STMT, curr_node.db_values())
        except KeyError: # arising from nodeid2obj[a cluster id]
            # We use [8:] to slice off the "cluster_" prefix on every rectangle
            # node that is actually a node group that will be backfilled (#80)
            curr_cluster = clusterid2obj[str(n)[8:]]
            component_node_count += curr_cluster.node_count
            component_edge_count += curr_cluster.edge_count
            component_total_length += curr_cluster.bp
            ep = n.attr[u'pos'].split(',')
            curr_cluster.xdot_x = float(ep[0])
            curr_cluster.xdot_y = float(ep[1])
            curr_cluster.xdot_width = float(n.attr[u'width'])
            curr_cluster.xdot_height = float(n.attr[u'height'])
            half_width_pts = \
                (config.POINTS_PER_INCH * (curr_cluster.xdot_width/2.0))
            half_height_pts = \
                (config.POINTS_PER_INCH * (curr_cluster.xdot_height/2.0))
            curr_cluster.xdot_left = curr_cluster.xdot_x - half_width_pts
            curr_cluster.xdot_right = curr_cluster.xdot_x + half_width_pts
            curr_cluster.xdot_bottom = curr_cluster.xdot_y - half_height_pts
            curr_cluster.xdot_top = curr_cluster.xdot_y + half_height_pts
            # Try to expand the component bounding box
            if curr_cluster.xdot_right > bounding_box_right:
                bounding_box_right = curr_cluster.xdot_right
            if curr_cluster.xdot_top > bounding_box_top:
                bounding_box_top = curr_cluster.xdot_top
            # Reconcile child nodes -- add to .db
            for n in curr_cluster.nodes:
                n.xdot_x = curr_cluster.xdot_left + n.xdot_rel_x
                n.xdot_y = curr_cluster.xdot_bottom + n.xdot_rel_y
                n.set_component_rank(component_size_rank)
                cursor.execute(NODE_INSERTION_STMT, n.db_values())
            # Reconcile child edges -- add to .db
            for e in curr_cluster.edges:
                # Adjust the control points to be relative to the entire
                # component. Also, try to expand to the component bounding box.
                p = 0
                coord_list = [float(c) for c in e.xdot_rel_ctrl_pt_str.split()]
                e.xdot_ctrl_pt_str = ""
                while p <= len(coord_list) - 2:
                    if p > 0:
                        e.xdot_ctrl_pt_str += " "
                    xp = coord_list[p]
                    yp = coord_list[p + 1]
                    e.xdot_ctrl_pt_str += str(curr_cluster.xdot_left + xp)
                    e.xdot_ctrl_pt_str += " "
                    e.xdot_ctrl_pt_str += str(curr_cluster.xdot_bottom + yp)
                    # Try to expand the component bounding box -- interior
                    # edges should normally be entirely within the bounding box
                    # of their node group, but complex bubbles might contain
                    # interior edges that go outside of the node group's b. box
                    if xp > bounding_box_right: bounding_box_right = xp
                    if yp > bounding_box_top: bounding_box_top = yp
                    p += 2
                # Save this edge in the .db
                cursor.execute(EDGE_INSERTION_STMT, e.db_values())
            # Save the cluster in the .db
            curr_cluster.component_size_rank = component_size_rank
            cursor.execute(CLUSTER_INSERTION_STMT, curr_cluster.db_values())
    # Record layout info of edges (that aren't inside node groups)
    for e in h.edges():
        # Since edges could point to/from node groups, we store their actual
        # source/target nodes in a comment attribute
        source_id, target_id = e.attr[u'comment'].split(',')
        source = nodeid2obj[source_id]
        curr_edge = source.outgoing_edge_objects[target_id]
        component_edge_count += 1
        if curr_edge.group != None:
            continue
        curr_edge.xdot_ctrl_pt_str, coord_list, curr_edge.xdot_ctrl_pt_count= \
            graph_objects.Edge.get_control_points(e.attr[u'pos'])
        if source_id != e[0]:
            # Adjust edge to point from interior node "source"'s tailport
            pts_height = source.xdot_height * config.POINTS_PER_INCH
            tail_y = source.xdot_y - (pts_height / 2)
            new_points = "%g %g " % (source.xdot_x, tail_y)
            xcps = curr_edge.xdot_ctrl_pt_str
            # Remove first control point (at tailport of the bounding box
            # rectangle of the node group that "source" is in)
            xcps = xcps[xcps.index(" ") + 1:]
            xcps = xcps[xcps.index(" ") + 1:]
            curr_edge.xdot_ctrl_pt_str = new_points + xcps
        if target_id != e[1]:
            # Adjust edge to point to interior node "target"'s headport
            target = nodeid2obj[target_id]
            pts_height = target.xdot_height * config.POINTS_PER_INCH
            tail_y = target.xdot_y + (pts_height / 2)
            new_points = "%g %g" % (target.xdot_x, tail_y)
            xcps = curr_edge.xdot_ctrl_pt_str
            # Remove last control point (at headport of the bounding box
            # rectangle of the node group that "target" is in)
            xcps = xcps[:xcps.rindex(" ")]
            xcps = xcps[:xcps.rindex(" ")]
            curr_edge.xdot_ctrl_pt_str = xcps + " " + new_points
        # Try to expand the component bounding box
        p = 0
        while p <= len(coord_list) - 2:
            x_coord = coord_list[p]
            y_coord = coord_list[p + 1]
            if x_coord > bounding_box_right: bounding_box_right = x_coord
            if y_coord > bounding_box_top: bounding_box_top = y_coord
            p += 2
        # Save this edge in the .db
        cursor.execute(EDGE_INSERTION_STMT, curr_edge.db_values())

    if not no_print:
        conclude_msg()
    # Output component information to the database
    cursor.execute(COMPONENT_INSERTION_STMT,
        (component_size_rank, component_node_count, component_edge_count,
        component_total_length, bounding_box_right, bounding_box_top))

    h.clear()
    h.close()
    component_size_rank += 1

t4 = time.time()
if no_print:
    conclude_msg()
print "Standard view layout time: %g seconds" % (t4 - t3)

operation_msg(config.DB_SAVE_MSG + "%s..." % (db_fn))
connection.commit()
conclude_msg()
# Close the database connection
connection.close()
