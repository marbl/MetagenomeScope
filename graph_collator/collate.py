#!/usr/bin/env python
# Converts assembly graph data to a DOT file, and lays out the DOT file
# using GraphViz to produce an XDOT output file that can be read by
# xdot2cy.js.
#
# This generates multiple DOT (intermediate) and XDOT (output) files,
# one for each connected component in the graph that contains a number of nodes
# greater than or equal to config.MIN_COMPONENT_SIZE. These files are named
# according to their connected components' relative sizes -- with a -o
# option of "output", the largest component will have output_1.xdot and
# output_1.gv (if preserved), the second largest component will have
# output_2.xdot and output_2.gv (if preserved), and so on.
#
# Syntax is:
#   ./collate_clusters.py -i (input file name) -o (file prefix)
#       [-d (output directory name)] [-pg] [-px] [-w]
#
# If you'd like to preserve the DOT file(s) after the program's execution, you
# can pass the argument -pg to this program to save the .gv files created.
# The .xdot file(s) generated after the program's execution (DOT files with
# additional layout information, created by GraphViz) can similarly be
# preserved if the -px argument is passed to this program.
#
# By default, this outputs db and (if -pg and/or -px is set) xdot/gv files
# to a directory created using the -o option. However, if you pass
# a directory name to -d, you can change the directory name to an arbitrary
# name that you specify. (Making use of this feature is recommended for most
# cases.)
#
# By default, this raises an error if any files in the output file directory
# will be overwritten. Passing the -w argument results in these errors being
# ignored and the corresponding files being overwritten, but note that an
# error be raised regardless if the output file directory name already
# exists as a non-directory file in the current directory. Also, note that
# files in the output file directory that have the same filename as any of the
# output files generated here (for an assembly graph where -o = "foobar" and
# one component exists, foobar_1.gv, foobar_1.xdot, foobar.db) but
# different case (e.g. FOOBAR_1.gv, Foobar_1.xdot, fooBar.db) will cause
# this script to break due to how os.path.exists() handles
# case-sensitive filesystems.
#
# NOTE that this just calls dot directly, and doesn't use the gv python library
# to do this. I guess there are some relative advantages and disadvantages to
# this approach, but for now it works fine. (If distributing this, we'd
# probably have to change this approach somewhat. Or we could just require
# the user have dot installed.)
# NOTE -- it turns out that the order of nodes in the graph actually changes
# the graph's output picture. Look into optimizing that somehow?

# For getting command-line arguments
from sys import argv
# For running dot, GraphViz' main layout manager
from subprocess import call
# For creating a directory in which we store xdot/gv files, and for file I/O
import os
# For checking I/O errors
import errno
# For parsing .xdot files
import re
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
i = 0
# Possible TODO here: use a try... block here to let the user know if they
# passed in arguments incorrectly, in a more user-friendly way
# Also we should probably validate that the filenames for -i and -o are
# valid (and we should prompt the user if this'll result in other files
# being overwritten)
for arg in argv:
    if arg == "-i":
        asm_fn = argv[i + 1]
    elif arg == "-o":
        output_fn = argv[i + 1]
        if dir_fn == "":
            dir_fn = output_fn
    elif arg == "-d":
        dir_fn = argv[i + 1]
    elif arg == "-pg":
        preserve_gv = True
    elif arg == "-px":
        preserve_xdot = True
    elif arg == "-w":
        overwrite = True
    i += 1

if asm_fn == "" or output_fn == "":
    raise ValueError("No input and/or output file name provided")

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

       Raises an IOError if:
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

def negate_node_id(id_string):
    """Negates a node ID.
    
       e.g. "c18" -> "18", "18" -> "c18"
    """
    if id_string[0] == 'c':
        return id_string[1:]
    else:
        return 'c' + id_string

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

def attempt_add_node_attr(text_line, n):
    """Attempts to add additional node information stored on a line of text
       from a .xdot file to a given node n.
       
       This function is sort of ugly, but it's decently efficient in the
       average case: moreso than just checking each compiled Regex against
       the line every time.
    """
    matches = config.NODEHGHT_RE.search(text_line)
    if matches != None:
        # Add height info
        n.xdot_height = float(matches.groups()[0])
    else:
        matches = config.NODEWDTH_RE.search(text_line)
        if matches != None:
            # Add width info
            n.xdot_width = float(matches.groups()[0])
        else:
            matches = config.NODEPOSN_RE.search(text_line)
            if matches != None:
                # Add positional info
                n.xdot_x = float(matches.groups()[0])
                n.xdot_y = float(matches.groups()[1])
            else:
                matches = config.NODESHAP_RE.search(text_line)
                if matches != None:
                    # Add shape info
                    n.xdot_shape = matches.groups()[0]

def attempt_find_ctrl_pts(text_line):
    """Attempts to find control point information stored on a line of text
       in a .xdot file.

       Returns a 3-tuple of the control point information ("" if no such
       information was found), the control point count (-1 if no information
       was found), and (True if more control point information remains to
       parse in following lines of text, False if this line contained all
       the control point information for the edge currently being parsed
       when this function was called, and None if no control point
       information at all was found).
    """
    c_matches = config.CPTSDECL_RE.search(text_line)
    if c_matches != None:
        more_left = True
        grps = c_matches.groups()
        point_count = int(grps[0])
        point_string = grps[1].strip() + " "
        e_c_matches = config.CPTS_END_RE.search(text_line)
        if e_c_matches != None:
            # If the control point declaration is only one line
            # long, don't try to parse > 1 lines of it
            more_left = False
        return point_string, point_count, more_left
    return "", -1, None

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
total_bp_length = 0
total_component_count = 0
# List of all the node lengths in the assembly. Used when calculating n50.
bp_length_list = []

# Create a SQLite database in which we store biological and graph layout
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
        (id text, length integer, dnafwd text, depth real,
        component_rank integer, x real, y real, w real, h real, shape text,
        parent_cluster_id text)""")
cursor.execute("""CREATE TABLE edges
        (source_id text, target_id text, multiplicity integer,
        component_rank integer, control_point_string text,
        control_point_count integer, parent_cluster_id text)""") 
cursor.execute("""CREATE TABLE clusters (cluster_id text,
        component_rank integer)""")
cursor.execute("""CREATE TABLE components
        (size_rank integer, node_count integer, edge_count integer,
        total_length integer, boundingbox_x real, boundingbox_y real)""")
cursor.execute("""CREATE TABLE assembly
        (filename text, filetype text, node_count integer,
        edge_count integer, component_count integer, total_length integer,
        n50 integer)""")
connection.commit()

# Process NODE (vertex) and ARC (edge) information
# TODO Adapt this to parse multiple types of assembly graph files.
# Currently supported:
# -LastGraph (Velvet)
# -GraphML (Bambus 3)
# Planned for support:
# -FASTG (SPAdes)
# -GFA
with open(asm_fn, 'r') as assembly_file:
    parsing_LastGraph = asm_fn.endswith(config.LASTGRAPH_SUFFIX)
    parsing_GraphML   = asm_fn.endswith(config.GRAPHML_SUFFIX)
    if parsing_LastGraph:
        graph_filetype = "LastGraph"
        # TODO -- Should we account for SEQ/NR information here?
        curr_node_id = ""
        curr_node_bp = 1
        curr_node_depth = 1
        curr_node_dnafwd = ""
        curr_node_dnarev = ""
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
                id1 = a[1] if a[1][0] != '-' else 'c' + a[1][1:]
                id2 = a[2] if a[2][0] != '-' else 'c' + a[2][1:]
                nid2 = negate_node_id(id2)
                nid1 = negate_node_id(id1)
                mult = int(a[3])
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2], mult)
                nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1], mult)
                # Record this edge for graph statistics
                total_edge_count += 1
            elif parsing_node:
                # If we're in the middle of parsing a node's info and
                # the current line doesn't match either a NODE or ARC
                # declaration, then it refers to the node's DNA sequence.
                if parsed_fwdseq:
                    # Parsing reverse sequence
                    curr_node_dnarev = line.strip()
                    n = graph_objects.Node(curr_node_id, curr_node_bp, False,
                            depth=curr_node_depth, dna_fwd=curr_node_dnafwd)
                    c = graph_objects.Node('c' + curr_node_id,
                            curr_node_bp, True, depth=curr_node_depth,
                            dna_fwd=curr_node_dnarev)
                    nodeid2obj[curr_node_id] = n
                    nodeid2obj['c' + curr_node_id] = c
                    # Record this node for graph statistics
                    # Note that recording these statistics here ensures that
                    # only "fully complete" node definitions are recorded.
                    total_node_count += 1
                    total_bp_length += curr_node_bp
                    bp_length_list.append(curr_node_bp)
                    bp_length_list.append(curr_node_bp)
                    # Clear temporary/marker variables for later use
                    curr_node_id = ""
                    curr_node_bp = 1
                    curr_node_dnafwd = ""
                    curr_node_dnarev = ""
                    parsing_node = False
                    parsed_fwdseq = False
                else:
                    # Parsing forward sequence (It's actually offset by a
                    # number of bp, so we should probably mention that in
                    # README or even in the Javascript graph viewer)
                    parsed_fwdseq = True
                    curr_node_dnafwd = line.strip()
    # TODO -- wait, is bp/length stored in GML files???
    # I guess for now I'm just going to treat every node as the same size
    elif parsing_GraphML:
        graph_filetype = "GraphML"
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
                    curr_node_bp = 100 # see TODO above
                elif line.startswith("   orientation"):
                    l = line.split()
                    curr_node_orientation = l[1] # either "FOW" or "REV"
                elif line.endswith("]\n"):
                    n = graph_objects.Node(curr_node_id, curr_node_bp,
                            (curr_node_orientation == '"REV"'))
                    nodeid2obj[curr_node_id] = n
                    # Record this node for graph statistics
                    total_node_count += 1
                    total_bp_length += curr_node_bp
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

# NOTE -- at this stage, the entire assembly graph file has been parsed.
# This means that graph_filetype, total_node_count, total_edge_count,
# total_bp_length, and bp_length_list are all finalized.

# Try to collapse special "groups" of Nodes (Bubbles, Ropes, etc.)
# As we check nodes, we add either the individual node (if it can't be
# collapsed) or its collapsed "group" (if it could be collapsed) to a list
# of nodes to draw, which will later be processed and output to the .gv file.
nodes_to_try_collapsing = nodeid2obj.values()
nodes_to_draw = []
nodes_to_draw_individually = []
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a group
    if n.used_in_collapsing:
        # If we've already collapsed n, don't try to collapse it again
        continue
    outgoing = n.outgoing_nodes
    # Cycle start positions can have >= 1 outgoing nodes, so we have to
    # check those first.
    cycle_validity, member_nodes = graph_objects.Cycle.is_valid_cycle(n)
    if cycle_validity:
        # Found a cycle!
        new_cycle = graph_objects.Cycle(*member_nodes)
        for x in member_nodes:
            x.used_in_collapsing = True
            x.group = new_cycle
        nodes_to_draw.append(new_cycle)
        clusterid2obj[new_cycle.id_string] = new_cycle
    elif len(outgoing) > 1:
        # Identify bubbles
        bubble_validity, member_nodes = graph_objects.Bubble.is_valid_bubble(n)
        if bubble_validity:
            # Found a bubble!
            new_bubble = graph_objects.Bubble(*member_nodes)
            for x in member_nodes:
                x.used_in_collapsing = True
                x.group = new_bubble
            nodes_to_draw.append(new_bubble)
            clusterid2obj[new_bubble.id_string] = new_bubble
    elif len(outgoing) == 1:
        # n could be the start of either a chain or a frayed rope.
        # Identify "frayed ropes"
        rope_validity, member_nodes = graph_objects.Rope.is_valid_rope(n)
        if rope_validity:
            # Found a frayed rope!
            new_rope = graph_objects.Rope(*member_nodes)
            for x in member_nodes:
                x.used_in_collapsing = True
                x.group = new_rope
            nodes_to_draw.append(new_rope)
            clusterid2obj[new_rope.id_string] = new_rope
        else:
            # Try to identify "chains" of nodes
            chain_validity,member_nodes = graph_objects.Chain.is_valid_chain(n)
            if chain_validity:
                # Found a chain!
                new_chain = graph_objects.Chain(*member_nodes)
                for x in member_nodes:
                    x.used_in_collapsing = True
                    x.group = new_chain
                nodes_to_draw.append(new_chain)
                clusterid2obj[new_chain.id_string] = new_chain
    if not n.used_in_collapsing:
        # If we didn't collapse the node in any groups while processing it --
        # that is, this node is not the "start" of any groups -- then
        # this node will later either be 1) drawn individually (not in any
        # group) or 2) collapsed, but as the middle/end/etc. of a group.
        # So we'll add this node to a special list and process other nodes,
        # and then later check to see if this node wound up used in a group.
        nodes_to_draw_individually.append(n)

# Check if non-start nodes were used in any groups (i.e. the group a given node
# was in has already been added to nodes_to_draw, and used_in_collapsing has
# been set to True). If not, then just draw the nodes individually.
# (We go to all this trouble to ensure that we don't accidentally draw a node
# twice or do something silly like that.)
for n in nodes_to_draw_individually:
    if not n.used_in_collapsing:
        # The node wasn't collapsed in any groups.
        nodes_to_draw.append(n)

# Identify connected components
# NOTE that nodes_to_draw only contains node groups and nodes that aren't in
# node groups. This allows us to run DFS on the nodes "inside" the node
# groups, preserving the groups' existence while not counting them in DFS.
# TODO make an actual component object? (so as to maintain both a list of
# nodes and a list of node groups)
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

graphVals = (os.path.basename(asm_fn), graph_filetype, total_node_count,
             total_edge_count, total_component_count, total_bp_length,
             n50(bp_length_list))
cursor.execute("INSERT INTO assembly VALUES (?,?,?,?,?,?,?)", graphVals)    

# Conclusion: Output (desired) components of nodes to the .gv file

component_size_rank = 1 # largest component is 1, the 2nd largest is 2, etc
for component in connected_components[:config.MAX_COMPONENTS]:
    # Since the component list is in descending order, if the current
    # component has less than config.MIN_COMPONENT_SIZE nodes then we're
    # done with displaying components
    if len(component.node_list) < config.MIN_COMPONENT_SIZE:
        break

    # OK, we're displaying this component.
    # Get the node info (for both normal nodes and clusters), and the edge
    # info (obtained by just getting the outgoing edge list for each normal
    # node in the component). This is an obviously limited subset of the
    # data we've ascertained from the file; once we parse the layout
    # information (.xdot) generated by GraphViz, we'll reconcile that data
    # with the previously-stored biological data.
    node_info, edge_info = component.node_and_edge_info()
    component_prefix = "%s_%d" % (output_fn, component_size_rank)

    gv_fullfn = os.path.join(dir_fn, component_prefix + ".gv")
    check_file_existence(gv_fullfn)
    # The flags we use here prevent race conditions (see
    # check_file_existence() documentation above).
    # Also, we use mode 0644 to just assign normal permissions to the output
    # files. os.open() should handle the mode alright on Windows and Unix
    # operating systems.
    with os.fdopen(os.open(gv_fullfn, flags, 0644), 'w') as gv_file:
        gv_file.write("digraph asm {\n");
        if config.GRAPH_STYLE != "":
            gv_file.write("\t%s;\n" % (config.GRAPH_STYLE))
        if config.GLOBALNODE_STYLE != "":
            gv_file.write("\tnode [%s];\n" % (config.GLOBALNODE_STYLE))
        if config.GLOBALEDGE_STYLE != "":
            gv_file.write("\tedge [%s];\n" % (config.GLOBALEDGE_STYLE))
        gv_file.write(node_info)
        gv_file.write(edge_info)
        gv_file.write("}")
    
    # output the graph (run GraphViz on the .gv file we just generated)
    xdot_fullfn = os.path.join(dir_fn, component_prefix + ".xdot")
    check_file_existence(xdot_fullfn)
    with os.fdopen(os.open(xdot_fullfn, flags, 0644), 'w') as xdot_file_w:
        print "Laying out connected component %d..." % (component_size_rank)
        call(["dot", gv_fullfn, "-Txdot"], stdout=xdot_file_w)
        print "Done laying out connected component %d." % (component_size_rank)
    # Read the .xdot file here and parse its layout information,
    # reconciling it with the corresponding nodes'/edges'/clusters'/
    # components'/graph information.
    # Then output that info to the SQLite database using the cursor and
    # connection variables we defined above.
    
    # Increment these vars. as we parse nodes/edges of this component
    component_node_count = 0
    component_edge_count   = 0
    component_total_length = 0
    with open(xdot_fullfn, 'r') as xdot_file_r:
        print "Parsing layout of component %d..." % (component_size_rank)
        # Like the xdot2cy.js parser I originally wrote, this parser assumes
        # perfectly formatted output (including 1-attribute-per-line, etc).
        # It's designed for use with xdot version 1.7, so other xdot
        # versions may cause this to break.

        # Misc. useful variables
        bounding_box = ()
        found_bounding_box = False
        # ...for when we're parsing a cluster
        parsing_cluster = False
        curr_cluster = None
        # ...for when we're parsing a node
        parsing_node = False
        curr_node = None
        # ...for when we're parsing an edge
        parsing_edge = False
        parsing_ctrl_pts = False
        curr_edge = None
        # Iterate line-by-line through the file, identifying cluster, node,
        # and edge declarations, attributes, and declaration closings as we
        # go along.
        for line in xdot_file_r:
            # Check for the .xdot file's bounding box
            if not parsing_cluster and not found_bounding_box:
                matches = config.BOUNDBOX_RE.search(line)
                if matches != None:
                    bounding_box = matches.groups()
                    found_bounding_box = True
                    continue
            # Check for cluster declarations
            if not parsing_cluster and not parsing_node and not parsing_edge:
                matches = config.CLUSDECL_RE.search(line)
                if matches != None:
                    parsing_cluster = True
                    curr_cluster = clusterid2obj[matches.groups()[0]]
                    continue
            # Check for cluster declaration ending
            if parsing_cluster and not parsing_node and not parsing_edge:
                matches = config.CLUS_END_RE.search(line)
                if matches != None:
                    curr_cluster.component_size_rank = component_size_rank
                    cursor.execute("""INSERT INTO clusters
                        VALUES (?,?)""", curr_cluster.db_values())
                    parsing_cluster = False
                    curr_cluster = None
                    continue
            # Check for node/edge declarations
            if not parsing_node and not parsing_edge:
                matches = config.NODEDECL_RE.search(line)
                if matches != None:
                    # Node declaration
                    parsing_node = True
                    curr_node = nodeid2obj[matches.groups()[0]]
                    attempt_add_node_attr(line, curr_node)
                    continue
                else:
                    matches = config.EDGEDECL_RE.search(line)
                    if matches != None:
                        # Edge declaration
                        parsing_edge = True
                        source = nodeid2obj[matches.groups()[0]]
                        sink_id = matches.groups()[1]
                        curr_edge = source.outgoing_edge_objects[sink_id]
                        # Check for control points declared on same line as
                        # edge declaration
                        cps, cpc, cps_more_left = attempt_find_ctrl_pts(line)
                        if cps != "":
                            curr_edge.xdot_ctrl_pt_str = cps
                            curr_edge.xdot_ctrl_pt_count = cpc
                            parsing_ctrl_pts = cps_more_left
                        continue
            # Check for node/edge declaration ending
            if parsing_node or parsing_edge:
                matches = config.NDEG_END_RE.search(line)
                if matches != None:
                    if parsing_node:
                        # Node declaration ending
                        attempt_add_node_attr(line, curr_node)
                        curr_node.set_component_rank(component_size_rank)
                        # Output node info to database
                        cursor.execute("""INSERT INTO nodes
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            curr_node.db_values())
                        component_node_count += 1
                        component_total_length += curr_node.bp
                        parsing_node = False
                        curr_node = None
                        continue
                    elif parsing_edge:
                        # Edge declaration ending
                        if parsing_ctrl_pts:
                            # As I mentioned in xdot2cy.js: I don't think
                            # this should ever happen (from what I can tell,
                            # _draw_ is always the 1st attr. of an edge in
                            # xdot), but this does work: if _draw_ is the
                            # last attr., we still detect all of it.
                            last_info = matches.groups()[0].strip()
                            last_info = last_info.replace('"', "")
                            curr_edge.xdot_ctrl_pt_str += last_info
                            parsing_ctrl_pts = False
                        # Verify this edge's control points are valid
                        ctrl_pt_coords = curr_edge.xdot_ctrl_pt_str.split()
                        ctrl_pt_coord_ct = len(ctrl_pt_coords)
                        if (ctrl_pt_coord_ct % 2 != 0 or
                              ctrl_pt_coord_ct / 2 !=
                                curr_edge.xdot_ctrl_pt_count):
                            raise IOError, "Invalid control points for \
                                edge %s -> %s in file %s." % \
                                (curr_edge.source_id, curr_edge.target_id,
                                xdot_fullfn)
                        if parsing_cluster:
                            curr_edge.group = curr_cluster
                        cursor.execute("""INSERT INTO edges
                            VALUES (?,?,?,?,?,?,?)""", curr_edge.db_values())
                        component_edge_count += 1
                        parsing_edge = False
                        curr_edge = None
                        continue
            # Check for node attributes in "intermediate lines"
            if parsing_node:
                attempt_add_node_attr(line, curr_node)
                continue
            # Check for edge control point info in "intermediate lines"
            if parsing_edge:
                if not parsing_ctrl_pts:
                    cps, cpc, cps_more_left = attempt_find_ctrl_pts(line)
                    if cps != "":
                        curr_edge.xdot_ctrl_pt_str = cps
                        curr_edge.xdot_ctrl_pt_count = cpc
                        parsing_ctrl_pts = cps_more_left
                    continue
                # If we're here, then we are parsing curr_edge's ctrl. pts.
                # on the current line.
                # Check for the ending of a control point declaration
                e_matches = config.CPTS_END_RE.search(line)
                if e_matches == None:
                    # Check for the continuation ("next lines", abbreviated
                    # as "NXL") of an ongoing control point declaration
                    n_matches = config.CPTS_NXL_RE.search(line)
                    if n_matches == None:
                        # Since parsing_ctrl_pts is True, something's off
                        # about the control points for this edge.
                        raise IOError, "Invalid control point statement \
                            for edge %s -> %s in file %s." % \
                            (curr_edge.source_id, curr_edge.target_id,
                            xdot_fullfn)
                    else:
                        curr_edge.xdot_ctrl_pt_str += \
                            n_matches.groups()[0].strip()
                        curr_edge.xdot_ctrl_pt_str += " "
                else:
                    curr_edge.xdot_ctrl_pt_str += e_matches.groups()[0].strip()
                    curr_edge.xdot_ctrl_pt_str += " "
                    parsing_ctrl_pts = False

        # If we didn't find a bounding box definition for the entire graph
        # within the xdot file, then we can't interpret its coordinates
        # meaningfully in the Javascript graph viewer. Raise an error.
        if not found_bounding_box:
            raise IOError, "No bounding box in %s." % (xdot_fullfn)
        print "Done parsing layout of component %d." % (component_size_rank)

    # Output component information to the database
    cursor.execute("""INSERT INTO components VALUES (?,?,?,?,?,?)""",
        (component_size_rank, component_node_count, component_edge_count,
        component_total_length, bounding_box[0], bounding_box[1]))

    # Unless the user requested their preservation, remove .gv/.xdot files
    if not preserve_gv:
        safe_file_remove(gv_fullfn)

    if not preserve_xdot:
        safe_file_remove(xdot_fullfn)

    component_size_rank += 1

connection.commit()
# Close the database connection
connection.close()
