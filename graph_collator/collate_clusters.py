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
# This differs from the normal collate_double.py in that it groups bubbles,
# ropes, chains into "clusters," while maintaining the original nodes'
# presence in the graph. So rather than "collapsing" parts of the graph,
# this actually adds more information to the graph.
# Also, this version has more bugfixes (re: chain detection, especially) and
# also has some more features added (cycle detection, etc) so this is
# essentially the "main" version of this program now.
#
# Syntax is:
#   ./collate_clusters.py -i (input file name) -o (xdot file prefix)
#       [-d (xdot/gv directory name)] [-p] [-w]
#
# If you'd like to preserve the DOT file(s) after the program's execution, you
# can pass the argument -p to this program to save the .gv files created.
#
# By default, this outputs xdot and (if -p is set) gv files to a directory
# created using the -o (xdot file prefix) option. However, if you pass
# a directory name to -d, you can change the directory name to an arbitrary
# name that you specify.
#
# By default, this raises an error if a file in the output file directory
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
# NOTE -- it turns out that the order of nodes in the graph actually changes the
# graph's output picture. Look into optimizing that somehow?
# TODO -- scale output? We can use the "size" setting of GraphViz, but that's
# in inches and also not universal (we don't want to scale down huge graphs to
# the point of being unreadable -- we want to acknowledge that some graphs are
# just going to take a while to display/view due to being really huge.)

# For getting command-line arguments
from sys import argv
# For running dot, GraphViz' main layout manager
from subprocess import call
# For creating a directory in which we store xdot/gv files
import os

from node_objectsc import *
from graph_config import *

# Get argument information
asm_fn = ""
output_fn = ""
dir_fn = ""
preserve = False
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
    elif arg == "-p":
        preserve = True
    elif arg == "-w":
        overwrite = True
    i += 1

if asm_fn == "" or output_fn == "":
    raise ValueError("No input and/or output file name provided")

try:
    os.mkdir(dir_fn)        # TODO sanitize this value? (e.g. for ..)
except:
    if not os.path.isdir(dir_fn):
        raise IOError, "%s already exists as file in CWD" % (dir_fn)

# Recursively runs depth-first search through the graph, starting at node n.
# At the end of execution, the value of seen_nodes returned will be whatever
# was in the initial list of seen_nodes combined with the entire connected
# component of the graph in which n is. (If you just want to find an entire
# connected component by itself, pass in [] for seen_nodes.)
def dfs(n, seen_nodes):
    n.seen_in_dfs = True
    seen_nodes.append(n)
    adjacent_nodes = n.outgoing_nodes + n.incoming_nodes
    for j in adjacent_nodes:
        if not j.seen_in_dfs:
            seen_nodes = dfs(j, seen_nodes)
    return seen_nodes

# Maps Node ID (as int) to the Node object in question
# This is nice, since it allows us to do things like nodeid2obj.values()
# to get a list of every Node object that's been processed
# (And, more importantly, to reconcile edge data with prev.-seen node data)
nodeid2obj = {}

# Process NODE (vertex) and ARC (edge) information
# TODO Adapt this to parse multiple types of assembly graph files.
# Currently supported:
# -Velvet (LastGraph)
# Working on supporting:
# -GraphML files (use a simple parsing_node, parsing_edge spec. shouldn't be
# too hard to implement. make sure to test thoroughly.)
with open(asm_fn, 'r') as assembly_file:
    parsing_LastGraph = asm_fn.endswith(LASTGRAPH_SUFFIX)
    parsing_GraphML   = asm_fn.endswith(GRAPHML_SUFFIX)
    # LastGraph files aren't too bad to parse, since all node/arc information
    # is on one line (aside from the actual nucleotide information).
    # TODO -- Should we account for SEQ/NR information here?
    if parsing_LastGraph:
        for line in assembly_file:
            if line[:4] == "NODE":
                l = line.split()
                i = int(l[1])
                bp = int(l[2])
                n = Node(i, bp, False)
                c = Node(-i, bp, True)
                nodeid2obj[i] = n
                nodeid2obj[-i] = c
            elif line[:3] == "ARC":
                a = line.split()
                i1 = int(a[1])
                i2 = int(a[2])
                nodeid2obj[i1].add_outgoing_edge(nodeid2obj[i2])
                nodeid2obj[-i2].add_outgoing_edge(nodeid2obj[-i1])
    # I'm not sure if GraphML is what you'd call an assembly graph file
    # format -- I think it's been generated by some assembler, but I don't
    # know which assembler generated it.
    # TODO -- wait, where is bp/length stored???
    # I guess for now I'm just going to treat every node as the same size
    if parsing_GraphML:
        # Record state -- parsing node or parsing edge?
        # (This is kind of a lazy approach, but to be fair it's actually
        # sort of efficient)
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
                            (curr_node_orientation == '"REV"'), False)
                    nodeid2obj[curr_node_id] = n
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
                    parsing_edge = False
                    curr_edge_src_id = None
                    curr_edge_tgt_id = None
            # Start parsing node
            elif line.endswith("node [\n"):
                parsing_node = True
            # Start parsing edge
            elif line.endswith("edge [\n"):
                parsing_edge = True

# Try to collapse special "groups" of Nodes (Bubbles, Ropes, etc.)
# As we check nodes, we add either the individual node (if it can't be
# collapsed) or its collapsed "group" (if it could be collapsed) to a list
# of nodes to draw, which will later be processed and output to the .gv file.
nodes_to_try_collapsing = nodeid2obj.values()
nodes_to_draw = []
nodes_to_draw_individually = []
for n in nodes_to_try_collapsing: # Test n as the "starting" node for a group
    if n.seen_in_collapsing:
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
            x.seen_in_collapsing = True
            x.group = new_cycle
        nodes_to_draw.append(new_cycle)
    elif len(outgoing) > 1:
        # Identify bubbles of depth 1 (1 node -> m adj nodes -> 1 node)
        bubble_validity, bubble_end = Bubble.is_valid_bubble(n)
        if bubble_validity:
            # Found a bubble!
            new_bubble = Bubble(n, outgoing, bubble_end)
            composite = [n] + outgoing + [bubble_end]
            for x in composite:
                x.seen_in_collapsing = True
                x.group = new_bubble
            nodes_to_draw.append(new_bubble)
    elif len(outgoing) == 1:
        # n could be the start of either a chain or a frayed rope.
        # Identify "frayed ropes"
        rope_validity, composite_nodes = Rope.is_valid_rope(n)
        if rope_validity:
            # Found a frayed rope!
            new_rope = Rope(*composite_nodes)
            for x in composite_nodes:
                x.seen_in_collapsing = True
                x.group = new_rope
            nodes_to_draw.append(new_rope)
        else:
            # Try to identify "chains" of nodes
            chain_validity, composite_nodes = Chain.is_valid_chain(n)
            if chain_validity:
                # Found a chain!
                new_chain = Chain(*composite_nodes)
                for x in composite_nodes:
                    x.seen_in_collapsing = True
                    x.group = new_chain
                nodes_to_draw.append(new_chain)
    if not n.seen_in_collapsing:
        # If we didn't collapse the node in any groups while processing it --
        # that is, this node is not the "start" of any groups -- then
        # this node will later either be 1) drawn individually (not in any
        # group) or 2) collapsed, but as the middle/end/etc. of a group.
        # So we'll add this node to a special list and process other nodes,
        # and then later check to see if this node wound up used in a group.
        nodes_to_draw_individually.append(n)

# Check if non-start nodes were used in any groups (i.e. the group a given node
# was in has already been added to nodes_to_draw, and seen_in_collapsing has
# been set to True). If not, then just draw the nodes individually.
# (We go to all this trouble to ensure that we don't accidentally draw a node
# twice or do something silly like that.)
for n in nodes_to_draw_individually:
    if not n.seen_in_collapsing:
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
    if not n.seen_in_ccomponent:
        # If n is actually a group of nodes: since we're representing groups
        # here as clusters, without any adjacencies themselves, we have to
        # run DFS on the nodes within the groups of nodes to discover them.
        node_list = []
        node_group_list = []
        if type(n) == Bubble:
            if n.start.seen_in_ccomponent:
                continue
            node_list = dfs(n.start, [])
        elif type(n) == Rope:
            if n.starts[0].seen_in_ccomponent:
                continue
            node_list = dfs(n.starts[0], [])
        elif type(n) == Chain or type(n) == Cycle:
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
            if m.seen_in_collapsing and m.group not in node_group_list:
                node_group_list.append(m.group)
        connected_components.append(Component(node_list, node_group_list))
connected_components.sort(reverse=True, key=lambda c: len(c.node_list))

# Conclusion: Output (desired) components of nodes to the .gv file

component_size_rank = 1 # largest component is 1, the 2nd largest is 2, etc
for component in connected_components[:MAX_COMPONENTS]:
    # Since the component list is in descending order, if the current
    # component has less than MIN_COMPONENT_SIZE nodes then we're done with
    # displaying components
    if len(component.node_list) < MIN_COMPONENT_SIZE:
        break

    # OK, we're displaying this component.
    node_info, edge_info = component.node_and_edge_info()
    component_prefix = "%s_%d" % (output_fn, component_size_rank)

    gv_fullfn = os.path.join(dir_fn, component_prefix + ".gv")
    if not overwrite and os.path.exists(gv_fullfn):
        raise IOError, "%s already exists" % (gv_fullfn)
    with open(gv_fullfn, 'w') as gvfile:
        gvfile.write("digraph asm {\n");
        if GRAPH_STYLE != "":
            gvfile.write("\t%s;\n" % (GRAPH_STYLE))
        if GLOBALNODE_STYLE != "":
            gvfile.write("\tnode [%s];\n" % (GLOBALNODE_STYLE))
        if GLOBALEDGE_STYLE != "":
            gvfile.write("\tedge [%s];\n" % (GLOBALEDGE_STYLE))
        gvfile.write(node_info)
        gvfile.write(edge_info)
        gvfile.write("}")
    
    # output the graph (run GraphViz on the .gv file we just generated)
    output_fullfn = os.path.join(dir_fn, component_prefix + ".xdot")
    if not overwrite and os.path.exists(output_fullfn):
        raise IOError, "%s already exists" % (output_fullfn)
    with open(output_fullfn, 'w') as output_file:
        print "Laying out connected component %d..." % (component_size_rank)
        call(["dot", gv_fullfn, "-Txdot", "-v"], stdout=output_file)
        print "Done laying out connected component %d." % (component_size_rank)
    
    if not preserve:
        call(["rm", gv_fullfn])

    component_size_rank += 1
