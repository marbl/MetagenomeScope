#!/usr/bin/env python
# Converts an assembly graph (LastGraph, GFA, Bambus 3 GML) to a DOT file,
# lays out the DOT file using GraphViz to produce XDOT output, and
# then reconciles the layout data with biological data in a SQLite .db
# file that can be read by the AsmViz viewer.
#
# For usage information, please see README.md in the root directory of AsmViz.

# For getting command-line arguments
from sys import argv
# For running dot, GraphViz' main layout manager
import pygraphviz
# For creating a directory in which we store xdot/gv files, and for file I/O
import os
# For checking I/O errors
import errno
# For interfacing with the SQLite Database
import sqlite3

import graph_objects
import config

# Get argument information
asm_fn = ""
output_fn = ""
dir_fn = ""
preserve_gv = False
preserve_xdot = False
overwrite = False
use_dna = True
double_graph = True
i = 1
# Possible TODO here: use a try... block here to let the user know if they
# passed in arguments incorrectly, in a more user-friendly way
# Also we should probably validate that the filenames for -i and -o are
# valid -- look into ArgParse?
for arg in argv[1:]:
    if (arg == "-i" or arg == "-o" or arg == "-d") and i == len(argv) - 1:
        # If this is the last argument, then no filename is given.
        # This is obviously invalid. (This allows us to avoid out of bounds
        # errors when accessing argv[i + 1].)
        raise ValueError, "No filename provided for %s" % (arg)
    if arg == "-i":
        asm_fn = argv[i + 1]
    elif arg == "-o":
        output_fn = argv[i + 1]
    elif arg == "-d":
        dir_fn = argv[i + 1]
    elif arg == "-pg":
        preserve_gv = True
    elif arg == "-px":
        preserve_xdot = True
    elif arg == "-w":
        overwrite = True
    elif arg == "-nodna":
        use_dna = False
    elif arg == "-s":
        double_graph = False
    elif i == 1 or argv[i - 1] not in ["-i", "-o", "-d"]:
        # If a valid "argument" doesn't match any of the above types,
        # then it must be a filename passed to -i, -o, or -d.
        # If it isn't (what this elif case checks for), 
        # then the argument is invalid and we need to raise an error.
        raise ValueError, "Invalid argument: %s" % (arg)
    i += 1

if asm_fn == "" or output_fn == "":
    raise ValueError, "No input and/or output file name provided"

if dir_fn == "":
    dir_fn = os.getcwd()

try:
    os.makedirs(dir_fn)
except:
    if not os.path.isdir(dir_fn):
        raise IOError, "%s already exists as a non-directory file" % (dir_fn)

# Assign flags for file creation
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
       certain flags (based on whether or not the user passed -w) set. This
       allows us to guarantee an error will be thrown and no data will be
       erroneously written in the first two cases, while (for most
       non-race-condition cases) allowing us to display a detailed error
       message to the user here, before we even try to open the file.
    """
    if os.path.exists(filepath):
        if os.path.isdir(filepath):
            raise IOError, "%s is a directory" % (filepath)
        if not overwrite:
            raise IOError, "%s already exists and -w is not set" % (filepath)
        return True
    return False

def safe_file_remove(filepath):
    """Safely (preventing race conditions of the file already being removed)
       removes a file located at the given file path.
    """
    try:
        os.remove(filepath)
    except OSError, error:
        if error.errno == errno.ENOENT:
            # Something removed the file before we could. That's alright.
            pass
        else:
            # Something strange happened -- maybe someone changed the file
            # to a directory, or something similarly odd. Raise the original
            # error to inform the user.
            raise

def dfs(n, seen_nodes):
    """Recursively runs depth-first search, starting at node n.

       At the end of this function's execution, the value of seen_nodes
       returned will be whatever was in the initial list of seen_nodes
       combined with all the nodes in the entire connected component of the
       graph in which n is.
       
       (If you just want to find an entire connected component by itself,
       you can just pass in [] for seen_nodes.)
    """
    n.seen_in_dfs = True
    seen_nodes.append(n)
    adjacent_nodes = n.outgoing_nodes + n.incoming_nodes
    for j in adjacent_nodes:
        if not j.seen_in_dfs:
            seen_nodes = dfs(j, seen_nodes)
    return seen_nodes

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
    
       e.g. "c18" -> "18", "18" -> "c18"
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
        raise ValueError, "N50 of an empty list does not exist"
    sorted_lengths = sorted(node_lengths, reverse=True)
    i = 0
    running_sum = 0
    half_total_length = 0.5 * sum(sorted_lengths)
    while running_sum < half_total_length:
        if i >= len(sorted_lengths):
            # This should never happen, but just in case
            raise IndexError, "N50 calculation error"
        running_sum += sorted_lengths[i]
        i += 1
    # Return length of shortest node that was used in the running sum
    return sorted_lengths[i - 1]

def save_aux_file(aux_filename, source):
    """Given a filename and a source of "input" for the file, writes to that
       file (using check_file_existence() and safe_file_remove() accordingly).

       If aux_filename ends with ".xdot", we assume that source is a
       pygraphviz.AGraph object of which we will write its "drawn" xdot output
       to the file.

       Otherwise, we assume that source is just a string of text to write
       to the file.
    """
    fullfn = os.path.join(dir_fn, aux_filename)
    ex = None
    try:
        ex = check_file_existence(fullfn)
    except IOError, e:
        # Don't save this file, but continue the script's execution
        print "Not saving %s: %s" % (fullfn, e)
    else:
        if ex:
            safe_file_remove(fullfn)
        with open(fullfn, 'w') as file_obj:
            if aux_filename.endswith(".xdot"):
                file_obj.write(source.draw(format="xdot"))
            else:
                file_obj.write(source)

# Maps Node ID (as int) to the Node object in question
# This is nice, since it allows us to do things like nodeid2obj.values()
# to get a list of every Node object that's been processed
# (And, more importantly, to reconcile edge data with prev.-seen node data)
nodeid2obj = {}
# Like nodeid2obj, but for preserving references to clusters (NodeGroups)
clusterid2obj = {}

# Pertinent Assembly-wide information we use 
graph_filetype = ""
total_node_count = 0
total_edge_count = 0
total_length = 0
total_gc_nt_count = 0
total_component_count = 0
# List of all the node lengths in the assembly. Used when calculating n50.
bp_length_list = []

# Below "with" block parses the assembly file.
# Please consult the README for the most accurate list of assembly graph
# filetypes supported.
with open(asm_fn, 'r') as assembly_file:
    # We don't really care about case in file extensions
    lowercase_asm_fn = asm_fn.lower()
    parsing_LastGraph = lowercase_asm_fn.endswith(config.LASTGRAPH_SUFFIX)
    parsing_GML   = lowercase_asm_fn.endswith(config.GRAPHML_SUFFIX)
    parsing_GFA       = lowercase_asm_fn.endswith(config.GFA_SUFFIX)
    if parsing_LastGraph:
        graph_filetype = "LastGraph"
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
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2], mult)
                # Only add implied edge if the edge does not imply itself
                # (see issue #105 on GitHub for context)
                if not (id1 == nid2 and id2 == nid1):
                    nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1], mult)
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
                    if not use_dna:
                        curr_node_dnarev = None
                    # In any case, now that we've parsed both the forward and
                    # reverse sequences for the node's DNA (or ignored the
                    # sequences, if the user passed the -nodna flag), we are
                    # done getting data for this node -- so we can create new
                    # Node objects to be added to the .db file and used in the
                    # graph layout.
                    n = graph_objects.Node(curr_node_id, curr_node_bp, False,
                            depth=curr_node_depth, gc_content=curr_node_gcfwd,
                            dna_fwd=curr_node_dnafwd)
                    c = graph_objects.Node('-' + curr_node_id,
                            curr_node_bp, True, depth=curr_node_depth,
                            gc_content=curr_node_gcrev,
                            dna_fwd=curr_node_dnarev)
                    nodeid2obj[curr_node_id] = n
                    nodeid2obj['-' + curr_node_id] = c
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
                    if not use_dna:
                        curr_node_dnafwd = None
    elif parsing_GML:
        graph_filetype = "GML"
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
        for line in assembly_file:
            # Record node attributes/detect end of node declaration
            if parsing_node:
                if line.startswith("   id"):
                    l = line.split()
                    curr_node_id = l[1]
                elif line.startswith("   orientation"):
                    l = line.split()
                    curr_node_orientation = l[1] # either "FOW" or "REV"
                elif line.startswith("   length"):
                    # fetch value from length attribute
                    l = line.split()
                    curr_node_bp = int(l[1].strip("\""))
                elif line.endswith("]\n"):
                    n = graph_objects.Node(curr_node_id, curr_node_bp,
                            (curr_node_orientation == '"REV"'))
                    nodeid2obj[curr_node_id] = n
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
                if line.startswith("   source"):
                    l = line.split()
                    curr_edge_src_id = l[1]
                elif line.startswith("   target"):
                    l = line.split()
                    curr_edge_tgt_id = l[1]
                elif line.endswith("]\n"):
                    nodeid2obj[curr_edge_src_id].add_outgoing_edge(
                            nodeid2obj[curr_edge_tgt_id])
                    total_edge_count += 1
                    # Clear tmp/marker vars
                    parsing_edge = False
                    curr_edge_src_id = None
                    curr_edge_tgt_id = None
            # Start parsing node
            elif line.endswith("node [\n"):
                parsing_node = True
            # Start parsing edge
            elif line.endswith("edge [\n"):
                parsing_edge = True
    elif parsing_GFA:
        graph_filetype = "GFA"
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
        for line in assembly_file:
            # Parsing a segment (node) line
            if line.startswith("S"):
                # For GFA files: given a + DNA seq, its - DNA seq is the
                # reverse complement of that DNA seq.
                l = line.split()
                curr_node_id = l[1]
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
                    total_gc_nt_count += (2 * gc_ct)
                else:
                    raise ValueError, \
                        "Sequence %s does not contain a DNA sequence" % \
                            (curr_node_id)
                if not use_dna:
                    curr_node_dnafwd = None
                    curr_node_dnarev = None
                nPos = graph_objects.Node(curr_node_id, curr_node_bp, False,
                        gc_content=curr_node_gc, dna_fwd=curr_node_dnafwd)
                nNeg = graph_objects.Node('-' + curr_node_id, curr_node_bp,
                        True,gc_content=curr_node_gc, dna_fwd=curr_node_dnarev)
                nodeid2obj[curr_node_id] = nPos
                nodeid2obj['-' + curr_node_id] = nNeg
                # Update stats
                total_node_count += 1
                total_length += curr_node_bp
                bp_length_list.append(curr_node_bp)
                bp_length_list.append(curr_node_bp)
            # Parsing a link (edge) line from some id1 to id2
            # I really like the way GFA handles edges; it makes this simple :)
            elif line.startswith("L"):
                a = line.split()
                id1 = a[1] if a[2] != '-' else '-' + a[1]
                id2 = a[3] if a[4] != '-' else '-' + a[3]
                nid2 = negate_node_id(id2)
                nid1 = negate_node_id(id1)
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2])
                # Only add implied edge if the edge does not imply itself
                # (see issue #105 on GitHub for context)
                if not (id1 == nid2 and id2 == nid1):
                    nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1])
                # Update stats
                total_edge_count += 1
    else:
        raise ValueError, "Invalid input filetype"

# NOTE -- at this stage, the entire assembly graph file has been parsed.
# This means that graph_filetype, total_node_count, total_edge_count,
# total_length, and bp_length_list are all finalized.

# Try to collapse special "groups" of Nodes (Bubbles, Ropes, etc.)
# As we check nodes, we add either the individual node (if it can't be
# collapsed) or its collapsed "group" (if it could be collapsed) to a list
# of nodes to draw, which will later be processed and output to the .gv file.

# We apply "precedence" here: identify all bubbles, then frayed ropes, then
# cycles, then chains. A TODO is making that precedence configurable
# (and generalizing this code to get rid of redundant stuff, maybe?)
nodes_to_try_collapsing = nodeid2obj.values()
nodes_to_draw = []
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

for n in nodes_to_try_collapsing: # Test n as the "starting" node for a cycle
    if n.used_in_collapsing:
        continue
    cycle_validity, member_nodes = graph_objects.Cycle.is_valid_cycle(n)
    if cycle_validity:
        # Found a cycle!
        new_cycle = graph_objects.Cycle(*member_nodes)
        nodes_to_draw.append(new_cycle)
        clusterid2obj[new_cycle.id_string] = new_cycle

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

# Add individual (not used in collapsing) nodes to the nodes_to_draw list
# We could build this list up at the start and then gradually remove nodes as
# we use nodes in collapsing, but remove() is an O(n) operation so that'd make
# the above runtime O(4n^2) or something, so I figure just doing this here is
# generally faster
for n in nodes_to_try_collapsing:
    if not n.used_in_collapsing:
        nodes_to_draw.append(n)

# Identify connected components
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
            node_list = dfs(n.nodes[0], [])
        else:
            # It's just a normal Node, but it could certainly be connected
            # to a group of nodes (not that it really matters)
            node_list = dfs(n, [])

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

# Now that we've done all our processing on the assembly graph, we create the
# output file: a SQLite database in which we store biological and graph layout
# information. This will be opened in the Javascript graph viewer.
db_fullfn = os.path.join(dir_fn, output_fn + ".db")
if check_file_existence(db_fullfn):
    # The user asked to overwrite this database via -w, so remove it
    safe_file_remove(db_fullfn)

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
cursor.execute("""CREATE TABLE nodes
        (id text, length integer, dnafwd text, gc_content real, depth real,
        component_rank integer, x real, y real, w real, h real, shape text,
        parent_cluster_id text)""")
cursor.execute("""CREATE TABLE edges
        (source_id text, target_id text, multiplicity integer,
        component_rank integer, control_point_string text,
        control_point_count integer, parent_cluster_id text)""") 
cursor.execute("""CREATE TABLE clusters (cluster_id text,
        component_rank integer, left real, bottom real, right real,
        top real)""")
cursor.execute("""CREATE TABLE components
        (size_rank integer, node_count integer, edge_count integer,
        total_length integer, boundingbox_x real, boundingbox_y real)""")
cursor.execute("""CREATE TABLE assembly
        (filename text, filetype text, node_count integer,
        edge_count integer, component_count integer, total_length integer,
        n50 integer, gc_content real)""")
connection.commit()

# Insert general assembly information into the database
graphVals = (os.path.basename(asm_fn), graph_filetype, total_node_count,
            total_edge_count, total_component_count, total_length,
            n50(bp_length_list), assembly_gc(total_gc_nt_count, total_length))
cursor.execute("INSERT INTO assembly VALUES (?,?,?,?,?,?,?,?)", graphVals)    

# Conclusion of script: Output (desired) components of nodes to the .gv file
component_size_rank = 1 # largest component is 1, the 2nd largest is 2, etc
no_print = False # used to reduce excess printing (see issue #133 on GitHub)
for component in connected_components[:config.MAX_COMPONENTS]:
    # Since the component list is in descending order, if the current
    # component has less than config.MIN_COMPONENT_SIZE nodes then we're
    # done with displaying components
    if len(component.node_list) < config.MIN_COMPONENT_SIZE:
        break
    if not no_print and len(component.node_list) < 5:
        no_print = True
        # The current component is included within the small component count
        small_component_ct = total_component_count - component_size_rank + 1
        comp_noun = "components" if small_component_ct > 1 else "component"
        print "Laying out %d " % (small_component_ct) + "small " + \
            "(containing < 5 nodes) remaining %s..." % (comp_noun)

    # OK, we're displaying this component.
    # Get the node info (for both normal nodes and clusters), and the edge
    # info (obtained by just getting the outgoing edge list for each normal
    # node in the component). This is an obviously limited subset of the
    # data we've ascertained from the file; once we parse the layout
    # information (.xdot) generated by GraphViz, we'll reconcile that data
    # with the previously-stored biological data.
    node_info, edge_info = component.node_and_edge_info()
    component_prefix = "%s_%d" % (output_fn, component_size_rank)

    # NOTE/TODO: Currently, we reduce each component of the asm. graph to a DOT
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
    if preserve_gv:
        save_aux_file(component_prefix + ".gv", gv_input)

    if not no_print:
        print config.START_LAYOUT_MSG + "%d..." % (component_size_rank)
    # lay out the graph in .xdot -- this step is the main bottleneck in the
    # python side of AsmViz
    h.layout(prog='dot')
    if not no_print:
        print config.DONE_LAYOUT_MSG + "%d." % (component_size_rank)
    # save the .xdot file if the user requested .xdot preservation
    if preserve_xdot:
        # AGraph.draw() doesn't perform graph positioning if layout()
        # has already been called on the given AGraph and no prog is
        # specified -- so this should be relatively fast
        save_aux_file(component_prefix + ".xdot", h)

    # Record the layout information of the graph's nodes, edges, and clusters
    if not no_print:
        print config.START_PARSING_MSG + "%d..." % (component_size_rank)

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
            cursor.execute( \
                "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                curr_node.db_values())
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
                cursor.execute( \
                    "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    n.db_values())
            # Reconcile child edges -- add to .db
            for e in curr_cluster.edges:
                # Don't bother trying to expand the component bounding box,
                # since interior edges should be entirely within their node
                # group's bounding box
                # However, we do adjust the control points to be relative to
                # the entire component
                p = 0
                coord_list = e.xdot_rel_ctrl_pt_str.split()
                e.xdot_ctrl_pt_str = ""
                while p <= len(coord_list) - 2:
                    if p > 0:
                        e.xdot_ctrl_pt_str += " "
                    xp = float(coord_list[p])
                    yp = float(coord_list[p + 1])
                    e.xdot_ctrl_pt_str += str(curr_cluster.xdot_left + xp)
                    e.xdot_ctrl_pt_str += " "
                    e.xdot_ctrl_pt_str += str(curr_cluster.xdot_bottom + yp)
                    p += 2
                # Save this edge in the .db
                cursor.execute("INSERT INTO edges VALUES (?,?,?,?,?,?,?)",
                    e.db_values())
            # Save the cluster in the .db
            curr_cluster.component_size_rank = component_size_rank
            cursor.execute("INSERT INTO clusters VALUES (?,?,?,?,?,?)",
                curr_cluster.db_values())
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
        # Skip the first control point
        pt_start = e.attr[u'pos'].index(" ") + 1
        curr_edge.xdot_ctrl_pt_str = \
            str(e.attr[u'pos'][pt_start:].replace(","," "))
        coord_list = curr_edge.xdot_ctrl_pt_str.split()
        # If len(coord_list) % 2 != 0 something has gone quite wrong
        if len(coord_list) % 2 != 0:
            raise ValueError, "Invalid edge control points for", curr_edge
        curr_edge.xdot_ctrl_pt_count = len(coord_list) / 2
        # Try to expand the component bounding box
        p = 0
        while p <= len(coord_list) - 2:
            x_coord = float(coord_list[p])
            y_coord = float(coord_list[p + 1])
            if x_coord > bounding_box_right: bounding_box_right = x_coord
            if y_coord > bounding_box_top: bounding_box_top = y_coord
            p += 2
        # Save this edge in the .db
        cursor.execute("INSERT INTO edges VALUES (?,?,?,?,?,?,?)",
            curr_edge.db_values())

    if not no_print:
        print config.DONE_PARSING_MSG + "%d." % (component_size_rank)
    # Output component information to the database
    cursor.execute("""INSERT INTO components VALUES (?,?,?,?,?,?)""",
        (component_size_rank, component_node_count, component_edge_count,
        component_total_length, bounding_box_right, bounding_box_top))

    h.clear()
    h.close()
    component_size_rank += 1

if no_print:
    print "Done laying out small components."

connection.commit()
# Close the database connection
connection.close()
