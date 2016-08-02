#!/usr/bin/env python
# Converts assembly graph data to a DOT file, and lays out the DOT file
# using GraphViz to produce an XDOT output file that can be read by
# xdot2cy.js.
#
# This generates multiple DOT (intermediate) and XDOT (output) files,
# one for each connected component in the graph that contains a number of nodes
# greater than or equal to MIN_COMPONENT_SIZE. These files are named
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
# exists as a non-directory file in the current directory.
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
# For creating a directory in which we store xdot/gv files
import os
# For parsing .xdot files
import re
# For interfacing with the SQLite Database
import sqlite3

from graph_objects import *
from config import *

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
    os.makedirs(dir_fn)        # TODO sanitize this value? (e.g. for ..)
except:
    if not os.path.isdir(dir_fn):
        raise IOError, "%s already exists as file in CWD" % (dir_fn)

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

def negate_contig_id(id_string):
    """Negates a contig ID.
    
       e.g. "c18" -> "18", "18" -> "c18"
    """
    if id_string[0] == 'c':
        return id_string[1:]
    else:
        return 'c' + id_string

def attempt_add_node_attr(text_line, n):
    """Attempts to add additional node information stored on a line of text
       from a .xdot file to a given node n.
       
       This function is sort of ugly, but it's decently efficient in the
       average case: moreso than just checking each compiled Regex against
       the line every time.
    """
    matches = NODEHGHT_RE.search(text_line)
    if matches != None:
        # Add height info
        n.xdot_height = float(matches.groups()[0])
    else:
        matches = NODEWDTH_RE.search(text_line)
        if matches != None:
            # Add width info
            n.xdot_width = float(matches.groups()[0])
        else:
            matches = NODEPOSN_RE.search(text_line)
            if matches != None:
                # Add positional info
                n.xdot_x = float(matches.groups()[0])
                n.xdot_y = float(matches.groups()[1])
            else:
                matches = NODESHAP_RE.search(text_line)
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
    c_matches = CPTSDECL_RE.search(text_line)
    if c_matches != None:
        more_left = True
        grps = c_matches.groups()
        point_count = int(grps[0])
        point_string = grps[1].strip() + " "
        e_c_matches = CPTS_END_RE.search(text_line)
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
total_contig_count = 0
total_edge_count = 0
total_bp_length = 0
total_component_count = 0

# Create a SQLite database in which we store biological and graph layout
# information. This will be opened in the Javascript graph viewer.
db_fullfn = os.path.join(dir_fn, output_fn + ".db")
if os.path.exists(db_fullfn):
    if not overwrite:
        raise IOError, "%s already exists" % (db_fullfn)
    else:
        # The user asked to overwrite this database via -w, so remove it
        call(["rm", db_fullfn])

connection = sqlite3.connect(db_fullfn)
cursor = connection.cursor()
cursor.execute("""CREATE TABLE contigs
        (id text, length integer, dnafwd text, depth real,
        component_rank integer, x real, y real, w real, h real, shape text,
        parent_cluster_id text)""")
cursor.execute("""CREATE TABLE edges
        (source_id text, target_id text, multiplicity integer,
        component_rank integer, control_point_string text,
        control_point_count integer, parent_cluster_id text)""") 
cursor.execute("""CREATE TABLE clusters (cluster_id text)""")
cursor.execute("""CREATE TABLE components
        (size_rank integer, contig_count integer, edge_count integer,
        total_length integer, boundingbox_x real, boundingbox_y real)""")
cursor.execute("""CREATE TABLE assembly
        (filetype text, contig_count integer, edge_count integer,
        component_count integer, total_length integer, n50 integer)""")
connection.commit()

# Process NODE (vertex) and ARC (edge) information
# TODO Adapt this to parse multiple types of assembly graph files.
# Currently supported:
# -LastGraph (Velvet)
# -GraphML (Bambus 3, IDBA-UD)
# Planned for support:
# -FASTG (SPAdes)
# -GFA
with open(asm_fn, 'r') as assembly_file:
    parsing_LastGraph = asm_fn.endswith(LASTGRAPH_SUFFIX)
    parsing_GraphML   = asm_fn.endswith(GRAPHML_SUFFIX)
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
                nid2 = negate_contig_id(id2)
                nid1 = negate_contig_id(id1)
                mult = int(a[3])
                nodeid2obj[id1].add_outgoing_edge(nodeid2obj[id2], mult)
                nodeid2obj[nid2].add_outgoing_edge(nodeid2obj[nid1], mult)
                # Record this edge for graph statistics; since each line
                # represents two edges, we record two edges for now
                total_edge_count += 2
            elif parsing_node:
                # If we're in the middle of parsing a contig's info and
                # the current line doesn't match either a NODE or ARC
                # declaration, then it refers to the contig's DNA sequence.
                if parsed_fwdseq:
                    # Parsing reverse sequence
                    curr_node_dnarev = line.strip()
                    n = Node(curr_node_id, curr_node_bp, False, \
                            depth=curr_node_depth, dna_fwd=curr_node_dnafwd)
                    c = Node('c' + curr_node_id, curr_node_bp, True, \
                            depth=curr_node_depth, dna_fwd=curr_node_dnarev)
                    nodeid2obj[curr_node_id] = n
                    nodeid2obj['c' + curr_node_id] = c
                    # Record this node for graph statistics
                    # (We include its RC node in these statistics for now)
                    # Note that recording these statistics here ensures that
                    # only "fully complete" node definitions are recorded.
                    total_contig_count += 2
                    total_bp_length += curr_node_bp
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
                    n = Node(curr_node_id, curr_node_bp, \
                            (curr_node_orientation == '"REV"'))
                    nodeid2obj[curr_node_id] = n
                    # Record this node for graph statistics
                    total_contig_count += 1
                    total_bp_length += curr_node_bp
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
                    nodeid2obj[curr_edge_src_id].add_outgoing_edge( \
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

# At this stage, the entire assembly graph file has been parsed.
# This means that graph_filetype, total_contig_count, total_edge_count, and
# total_bp_length are all finalized.

#print "Assembly graph type: ", graph_filetype
#print "Node ct. : ", total_contig_count
#print "Edge ct. : ", total_edge_count
#print "Total len: ", total_bp_length

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
    cycle_validity, composite_nodes = Cycle.is_valid_cycle(n)
    if cycle_validity:
        # Found a cycle!
        new_cycle = Cycle(*composite_nodes)
        for x in composite_nodes:
            x.used_in_collapsing = True
            x.group = new_cycle
        nodes_to_draw.append(new_cycle)
        clusterid2obj[new_cycle.id_string] = new_cycle
    elif len(outgoing) > 1:
        # Identify bubbles
        bubble_validity, composite_nodes = Bubble.is_valid_bubble(n)
        if bubble_validity:
            # Found a bubble!
            new_bubble = Bubble(*composite_nodes)
            for x in composite_nodes:
                x.used_in_collapsing = True
                x.group = new_bubble
            nodes_to_draw.append(new_bubble)
            clusterid2obj[new_bubble.id_string] = new_bubble
    elif len(outgoing) == 1:
        # n could be the start of either a chain or a frayed rope.
        # Identify "frayed ropes"
        rope_validity, composite_nodes = Rope.is_valid_rope(n)
        if rope_validity:
            # Found a frayed rope!
            new_rope = Rope(*composite_nodes)
            for x in composite_nodes:
                x.used_in_collapsing = True
                x.group = new_rope
            nodes_to_draw.append(new_rope)
            clusterid2obj[new_rope.id_string] = new_rope
        else:
            # Try to identify "chains" of nodes
            chain_validity, composite_nodes = Chain.is_valid_chain(n)
            if chain_validity:
                # Found a chain!
                new_chain = Chain(*composite_nodes)
                for x in composite_nodes:
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
        if issubclass(type(n), NodeGroup):
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
        connected_components.append(Component(node_list, node_group_list))
        total_component_count += 1
connected_components.sort(reverse=True, key=lambda c: len(c.node_list))

#print "Total component ct.: ", total_component_count

# Conclusion: Output (desired) components of nodes to the .gv file

component_size_rank = 1 # largest component is 1, the 2nd largest is 2, etc
for component in connected_components[:MAX_COMPONENTS]:
    # Since the component list is in descending order, if the current
    # component has less than MIN_COMPONENT_SIZE nodes then we're done with
    # displaying components
    if len(component.node_list) < MIN_COMPONENT_SIZE:
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
    if not overwrite and os.path.exists(gv_fullfn):
        raise IOError, "%s already exists" % (gv_fullfn)
    with open(gv_fullfn, 'w') as gv_file:
        gv_file.write("digraph asm {\n");
        if GRAPH_STYLE != "":
            gv_file.write("\t%s;\n" % (GRAPH_STYLE))
        if GLOBALNODE_STYLE != "":
            gv_file.write("\tnode [%s];\n" % (GLOBALNODE_STYLE))
        if GLOBALEDGE_STYLE != "":
            gv_file.write("\tedge [%s];\n" % (GLOBALEDGE_STYLE))
        gv_file.write(node_info)
        gv_file.write(edge_info)
        gv_file.write("}")
    
    # output the graph (run GraphViz on the .gv file we just generated)
    xdot_fullfn = os.path.join(dir_fn, component_prefix + ".xdot")
    if not overwrite and os.path.exists(xdot_fullfn):
        raise IOError, "%s already exists" % (xdot_fullfn)
    with open(xdot_fullfn, 'w') as xdot_file_w:
        print "Laying out connected component %d..." % (component_size_rank)
        call(["dot", gv_fullfn, "-Txdot"], stdout=xdot_file_w)
        print "Done laying out connected component %d." % (component_size_rank)
    # Read the .xdot file here and parse its layout information,
    # reconciling it with the corresponding nodes'/edges'/clusters'/
    # components'/graph information.
    # Then output that info to the SQLite database using the cursor and
    # connection variables we defined above.
    
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
                matches = BOUNDBOX_RE.search(line)
                if matches != None:
                    bounding_box = matches.groups()
                    found_bounding_box = True
                    continue
            # Check for cluster declarations
            if not parsing_cluster and not parsing_node and not parsing_edge:
                matches = CLUSDECL_RE.search(line)
                if matches != None:
                    parsing_cluster = True
                    curr_cluster = clusterid2obj[matches.groups()[0]]
                    continue
            # Check for cluster declaration ending
            if parsing_cluster and not parsing_node and not parsing_edge:
                matches = CLUS_END_RE.search(line)
                if matches != None:
                    curr_cluster.component_size_rank = component_size_rank
                    parsing_cluster = False
                    curr_cluster = None
                    continue
            # Check for node/edge declarations
            if not parsing_node and not parsing_edge:
                matches = NODEDECL_RE.search(line)
                if matches != None:
                    # Node declaration
                    parsing_node = True
                    curr_node = nodeid2obj[matches.groups()[0]]
                    attempt_add_node_attr(line, curr_node)
                    continue
                else:
                    matches = EDGEDECL_RE.search(line)
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
                matches = NDEG_END_RE.search(line)
                if matches != None:
                    if parsing_node:
                        # Node declaration ending
                        attempt_add_node_attr(line, curr_node)
                        curr_node.set_component_rank(component_size_rank)
                        # Output node info to database
                        cursor.execute("""INSERT INTO contigs
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", \
                            curr_node.db_values())
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
                                (curr_edge.source_id, curr_edge.target_id, \
                                xdot_fullfn)
                        if parsing_cluster:
                            curr_edge.group = curr_cluster
                        cursor.execute("""INSERT INTO edges
                            VALUES (?,?,?,?,?,?,?)""", curr_edge.db_values())
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
                e_matches = CPTS_END_RE.search(line)
                if e_matches == None:
                    # Check for the continuation ("next lines", abbreviated
                    # as "NXL") of an ongoing control point declaration
                    n_matches = CPTS_NXL_RE.search(line)
                    if n_matches == None:
                        # Since parsing_ctrl_pts is True, something's off
                        # about the control points for this edge.
                        raise IOError, "Invalid control point statement \
                            for edge %s -> %s in file %s." % \
                            (curr_edge.source_id, curr_edge.target_id, \
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

    if not preserve_gv:
        call(["rm", gv_fullfn])

    if not preserve_xdot:
        call(["rm", xdot_fullfn])

    component_size_rank += 1

graphVals = (graph_filetype, total_contig_count, total_edge_count, \
             total_component_count, total_bp_length, 0)
cursor.execute("INSERT INTO assembly VALUES (?,?,?,?,?,?)", graphVals)    
connection.commit()
# Close the database connection
connection.close()
