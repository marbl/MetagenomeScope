# This file contains various objects defining nodes, node groups, and edges
# in the assembly graph. We use these objects to simplify the process of
# storing information about the assembly graph.

import config
from math import log, sqrt
import pygraphviz

class Edge(object):
    """A generic edge, used for storing layout data (e.g. control points)
       and, if applicable for this type of assembly file, biological
       metadata (e.g. multiplicity, as given in LastGraph files).
    """
    def __init__(self, source_id, target_id, multiplicity=None):
        """Initializes the edge and all of its attributes."""
        self.source_id = source_id
        self.target_id = target_id
        self.multiplicity = multiplicity
        # For if the edge is an "interior" edge of a node group
        self.group = None
        # Will be replaced with the size rank of the connected component to
        # which this edge belongs
        self.component_size_rank = -1
        # Misc. layout data that we'll eventually record here if we decide
        # to lay out the component in which this edge is stored
        self.xdot_ctrl_pt_str = None
        self.xdot_ctrl_pt_count  = None

    def db_values(self):
        """Returns a tuple containing the values of this edge.

           The tuple is created to be inserted into the "edges" database
           table.

           Should be called after parsing .xdot layout information for this
           edge.
        """
        group_id = None
        if self.group != None:
            group_id = self.group.cy_id_string
        return (self.source_id, self.target_id, self.multiplicity,
                self.component_size_rank, self.xdot_ctrl_pt_str,
                self.xdot_ctrl_pt_count, group_id)

    def __repr__(self):
        return "Edge from %s to %s" % (self.source_id, self.target_id)

class Node(object):
    """A generic node. Used for representing individual contigs/scaffolds,
       and as the superclass for groups of nodes.
    """
    def __init__(self, id_string, bp, is_complement, depth=None,
                 gc_content=None, dna_fwd=None):
        """Initializes the object. bp initially stood for "base pairs," but
           it really just means the length of this node. In single graphs
           that's measured in bp and in double graphs that's measured in nt.
           
           We'll scale it later if we actually decide to draw this node.
        """
        self.id_string = id_string
        self.bp = bp
        self.depth = depth
        self.gc_content = gc_content
        self.dna_fwd = dna_fwd
        # If True, we use the "flipped" node style
        self.is_complement = is_complement
        # List of nodes to which this node has an outgoing edge
        self.outgoing_nodes = []
        # List of nodes from which this node has an incoming edge
        self.incoming_nodes = []
        # Dict of Edge objects that have this node as a source -- used for
        # storing/reading more detailed edge information, not used for graph
        # traversal. Edge objects are stored as values, and their
        # corresponding key is the sink (target) node of the edge.
        # ...e.g. for 1->2, 1->3, 1->4, outgoing_edge_objects would look like
        # {2: Edge(1, 2), 3: Edge(1, 3), 4: Edge(1, 4)}
        self.outgoing_edge_objects = {}
        # Flag variables we use to make DFS/finding connected components
        # more efficient (maintaining a list or dict of this info is more
        # expensive than just using attributes, like this)
        self.seen_in_dfs = False
        self.seen_in_ccomponent = False
        self.used_in_collapsing = False
        # If we decide to subsume a node group into another node group,
        # thus removing the initial node group, we use this flag to
        # mark that node group to not be drawn.
        self.is_subsumed = False
        # When we collapse nodes into a node group, we change this variable
        # to reference the NodeGroup object in question
        self.group = None
        # Reference to the "size rank" (1 for largest, 2 for 2nd largest,
        # ...) of the connected component to which this node belongs.
        self.component_size_rank = -1
        # Misc. layout data that we'll eventually record here if we decide
        # to lay out the component in which this node is stored
        self.xdot_width  = None
        self.xdot_height = None
        self.xdot_x      = None
        self.xdot_y      = None
        self.xdot_shape  = None
        # Optional layout data (used for nodes within subgraphs)
        self.xdot_rel_x  = None
        self.xdot_rel_y  = None
        
    def get_height(self):
        """Calculates the "height" of this node.
        
           Returns a 2-tuple of the node height and an int indicating
           any rounding up/down done
           (a value of 0 indicates no rounding,
           positive values indicate rounding down being done,
           negative values indicate rounding up being done).
           
           NOTE that this shouldn't be confused with the .xdot_height
           property, which represents the actual height of this node as
           determined by GraphViz.
        """
        h = log(self.bp, config.CONTIG_SCALING_LOG_BASE)
        if h > config.MAX_CONTIG_HEIGHT:
            h = config.MAX_CONTIG_HEIGHT
            rounding_done = 1
        elif h < config.MIN_CONTIG_HEIGHT:
            h = config.MIN_CONTIG_HEIGHT
            rounding_done = -1
        else:
            rounding_done = 0
        return (h, rounding_done)

    def node_info(self, custom_shape=None, custom_style=None):
        """Returns a string representing this node that can be used in a .dot
           file for input to GraphViz.

           You can change custom_shape to give the node a particular shape; by
           default, this uses config.BASIC_NODE_SHAPE for "normal" nodes and
           config.RCOMP_NODE_SHAPE for "reverse complement" nodes.
           I don't think anything in this program uses custom_shape any
           more; I used to use it when we collapsed node groups into squares
           on the Python side of this program, and not in the JS side.

           If custom_style is passed (e.g. as config.BUBBLE_STYLE or
           config.FRAYEDROPE_STYLE) then that style information will be used.
           By default, nodes that have been rounded up or down in height will
           use special style information, but custom_style overrides that.
        """
        h, r = self.get_height()
        info = "\t%s [height=%g,width=%g,shape=" % \
                (self.id_string, h, config.WIDTH_HEIGHT_RATIO * h)
        if custom_shape == None:
            if not self.is_complement:
                info += config.BASIC_NODE_SHAPE
            else:
                info += config.RCOMP_NODE_SHAPE
        else:
            info += custom_shape
        if custom_style == None:
            if r > 0:
               info += ',' + config.ROUNDED_DN_STYLE
            elif r < 0:
               info += ',' + config.ROUNDED_UP_STYLE
        else:
            info += ',' + custom_style
        info += "];\n"
        return info

    def add_outgoing_edge(self, node2, multiplicity=None):
        """Adds an outgoing edge from this node to another node, and adds an
           incoming edge from the other node referencing this node.

           Also adds an Edge with the given multiplicity data to this node's
           dict of outgoing Edge objects.
        """
        self.outgoing_nodes.append(node2)
        node2.incoming_nodes.append(self)
        self.outgoing_edge_objects[node2.id_string] = \
            Edge(self.id_string, node2.id_string, multiplicity)

    def edge_info(self, constrained_nodes=None):
        """Returns a GraphViz-compatible string containing all information
           about outgoing edges from this node.

           Useful for only printing edges relevant to the nodes we're
           interested in.

           If constrained_nodes is not None, then it is interpreted as a list
           of nodes to "constrain" the edges: that is, edges pointing to the
           nodes within this list are the only edges whose info will be
           included in the returned string.
        """
        o = ""
        # Since we only care about the target ID and not about any other
        # edge data it's most efficient to just traverse self.outgoing_nodes
        for m in self.outgoing_nodes:
            if (constrained_nodes is None) or (m in constrained_nodes):
                o += "\t%s -> %s\n" % (self.id_string, m.id_string)
        return o

    def set_component_rank(self, component_size_rank):
        """Sets the component_size_rank property of this node and of all
           its outgoing edges.
        """
        self.component_size_rank = component_size_rank
        for e in self.outgoing_edge_objects.values():
            e.component_size_rank = component_size_rank

    def db_values(self):
        """Returns a tuple of the "values" of this Node.
        
           This value will be used to populate the database's "contigs"
           table with information about this node.
           
           Note that this doesn't really apply to NodeGroups, since they
           don't have most of these attributes defined. I'll define a more
           specific NodeGroup.db_values() function later.
           
           Also, this shouldn't be called until after this Node's layout
           information has been parsed from an .xdot file and recorded.
        """
        # See collate.py for the most up-to-date specifications of how this
        # table is laid out.
        # The "parent cluster id" field can be either an ID or NULL
        # (where NULL denotes no parent cluster), so we decide that here.
        group_id = None
        if self.group != None:
            group_id = self.group.cy_id_string
        length = self.bp
        return (self.id_string, length, self.dna_fwd, self.gc_content,
                self.depth, self.component_size_rank, self.xdot_x,
                self.xdot_y, self.xdot_width, self.xdot_height,
                self.xdot_shape, group_id)

    def __repr__(self):
        """For debugging -- returns a str representation of this node."""
        return "Node %s" % (self.id_string)

class NodeGroup(Node):
    """A group of nodes, accessible via the .nodes attribute.

       Note that node groups here are used to create "clusters" in GraphViz,
       in which a cluster is composed of >= 1 child nodes.

       (This is similar to Cytoscape.js' concept of a "compound node," for
       reference -- with the distinction that in Cytoscape.js a compound
       node is an actual "node," while in GraphViz a cluster is merely a
       "subgraph.")
    """
    
    def __init__(self, group_prefix, group_style, nodes):
        """Initializes the node group, given all the Node objects comprising
           the node group, a prefix character for the group (i.e. 'R' for
           frayed ropes, 'B' for bubbles, 'C' for chains, 'Y' for cycles),
           and a GraphViz style setting for the group (generally
           from config.py).

           Note that we use two IDs for Node Groups: one with '-'s replaced
           with 'c's (since GraphViz only allows '-' in IDs when it's the
           first character and the other ID characters are numbers), and one
           with the original ID names. The 'c' version is passed into GraphViz,
           and the '-' version is passed into the .db file to be used in
           Cytoscape.js.
        """
        self.node_count = 0
        self.group_style = group_style
        self.bp = 0
        self.gv_id_string = "%s" % (group_prefix)
        self.cy_id_string = "%s" % (group_prefix)
        self.nodes = []
        childid2obj = {}
        for n in nodes:
            self.node_count += 1
            self.bp += n.bp
            self.gv_id_string += "%s_" % (n.id_string.replace('-', 'c'))
            self.cy_id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
            n.used_in_collapsing = True
            n.group = self
            childid2obj[n.id_string] = n
        self.gv_id_string = self.gv_id_string[:-1] # remove last underscore
        self.cy_id_string = self.cy_id_string[:-1] # remove last underscore
        # pipe .gv into pygraphviz to lay out this node group
        gv_input = ""
        gv_input += "digraph nodegroup {\n"
        # TODO abstract this header generation code to some function in this
        # file that will be called by here, and by collate?
        # ... or just rework the _STYLE variables to make them easier to
        # integrate, I suppose.
        # ... or just deal with 6 lines of repeated code, I guess -- not the
        # worst thing that we could be dealing with :)
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            gv_input += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)
        gv_input += self.node_info()
        for n in self.nodes:
            # Ensure that only the edges that point to nodes that are within
            # the node group are present; ensures layout is restricted to just
            # the node group in question
            gv_input += n.edge_info(constrained_nodes=self.nodes)
        gv_input += "}"
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog='dot')
        # Obtain cluster width and height from the layout
        bounding_box_text = cg.subgraphs()[0].graph_attr[u'bb']
        bounding_box_numeric = [float(y) for y in bounding_box_text.split(',')]
        self.xdot_width = bounding_box_numeric[2] - bounding_box_numeric[0]
        self.xdot_height = bounding_box_numeric[3] - bounding_box_numeric[1]
        # Obtain node info
        # NOTE: we could iterate over the subgraph's nodes or over the entire
        # graph (cg)'s nodes -- same result, since the only nodes in the graph
        # are in the subgraph.
        for n in cg.nodes():
            curr_node = childid2obj[str(n)]
            # Record the relative position (within the node group's bounding
            # box) of this child node.
            ep = n.attr[u'pos'].split(',')
            curr_node.xdot_rel_x = float(ep[0])
            curr_node.xdot_rel_y = float(ep[1])
            curr_node.xdot_width = float(n.attr[u'width'])
            curr_node.xdot_height = float(n.attr[u'height'])
        # TODO: obtain and assign edge layout info
        self.xdot_left = None
        self.xdot_bottom = None
        self.xdot_right = None
        self.xdot_top = None
        super(NodeGroup, self).__init__(self.gv_id_string, self.bp, False)

    def node_info(self):
        """Returns a string of the node_info() of this NodeGroup.

           This finds the node_info() of all its children, naturally.
        """
        info = "subgraph cluster_%s {\n" % (self.gv_id_string)
        if config.GLOBALCLUSTER_STYLE != "":
            info += "\t%s;\n" % (config.GLOBALCLUSTER_STYLE)
        for n in self.nodes:
            info += n.node_info()
        info += self.group_style + "}\n"
        return info

    def db_values(self):
        """Returns a tuple containing the values associated with this group.
           Should be called after parsing and assigning .xdot bounding box
           values accordingly.
        """
        return (self.cy_id_string, self.component_size_rank, self.xdot_left,
                self.xdot_bottom, self.xdot_right, self.xdot_top)

class Bubble(NodeGroup):
    """A group of nodes collapsed into a Bubble. This consists of one
       node which points to >= 2 "middle" nodes, all of which in turn point
       to one "end" node.
    """
    def __init__(self, *nodes):
        """Initializes the Bubble, given a list of nodes comprising it."""
        super(Bubble, self).__init__('B', config.BUBBLE_STYLE, nodes)

    @staticmethod
    def is_valid_bubble(s):
        """Returns a 2-tuple of True and a list of the nodes comprising the
           Bubble if a Bubble defined with the given start node is valid.
           Returns a 2-tuple of (False, None) if such a Bubble would be
           invalid.
           
           NOTE that this assumes that s has > 1 outgoing edges.
        """
        if s.used_in_collapsing: return False, None
        # Get a list of the first node on each divergent path through this
        # (potential) bubble
        m1_nodes = s.outgoing_nodes
        # The bubble's ending node will be recorded here
        e_node = None
        # We keep a list of chains to mark as "subsumed" (there's a max
        # of p chains that will be in this list, where p = the number of
        # divergent paths through this bubble)
        chains_to_subsume = []
        # Traverse through the bubble's divergent paths, checking for
        # validity and recording nodes
        # List of all middle nodes (divergent paths) in the bubble
        m_nodes = []
        # List of all nodes that are the "end" of divergent paths in the bubble
        mn_nodes = []
        for n in m1_nodes:
            if len(n.incoming_nodes) != 1 or len(n.outgoing_nodes) != 1:
                return False, None
            # Now we know that this path is at least somewhat valid, get
            # all the middle nodes on it and the ending node from it.
            chain_validity, path_nodes = Chain.is_valid_chain(n)
            if not chain_validity:
                # We could have already grouped the middle nodes of this rope
                # into a chain, which would be perfectly valid
                # (Chain.is_valid_chain() rejects Chains composed of nodes that
                # have already been used in collapsing)
                if n.used_in_collapsing:
                    if type(n.group) == Chain:
                        path_nodes = n.group.nodes
                        path_end = path_nodes[len(path_nodes)-1].outgoing_nodes
                        # The divergent paths of a bubble must converge
                        if len(path_end) != 1:
                            return False, None
                        if e_node == None:
                            e_node = path_end[0]
                        # If the divergent paths of a bubble don't converge to
                        # the same ending node, then it isn't a bubble
                        elif e_node != path_end[0]:
                            return False, None
                        m_nodes += path_nodes
                        mn_nodes.append(path_nodes[len(path_nodes) - 1])
                        chains_to_subsume.append(n.group)
                    else:
                        # if this path has been grouped into a pattern that 
                        # isn't a chain, don't identify this as a bubble
                        return False, None
                # Or we just have a single middle node (assumed if no middle
                # chain exists/could exist)
                else:
                    # Like above, record or check ending node
                    if e_node == None:
                        e_node = n.outgoing_nodes[0]
                    elif e_node != n.outgoing_nodes[0]:
                        return False, None
                    # And if that worked out, then record this path
                    m_nodes.append(n)
                    mn_nodes.append(n)
            else:
                # The middle nodes form a chain that has not been "created" yet
                # This makes this a little easier for us.
                path_end = path_nodes[len(path_nodes) - 1].outgoing_nodes
                if len(path_end) != 1:
                    return False, None
                if e_node == None:
                    e_node = path_end[0]
                elif e_node != path_end[0]:
                    return False, None
                m_nodes += path_nodes
                mn_nodes.append(path_nodes[len(path_nodes) - 1])
            # Now we have the middle and end nodes of the graph stored.

        # Check ending node
        if e_node.used_in_collapsing:
            return False, None
        # If the ending node has any incoming nodes that are not in
        # mn_nodes, then reject this bubble.
        elif set(e_node.incoming_nodes) != set(mn_nodes):
            return False, None
        # If the bubble is cyclical, reject it
        # (checking the outgoing/incoming nodes of m1_nodes, and only
        # allowing chains or singleton paths in m_nodes, means we should
        # never have an outgoing node from e to anything in m_nodes by this
        # point
        elif s in e_node.outgoing_nodes:
            return False, None
        
        # Check entire bubble structure, to ensure all nodes are distinct
        composite = [s] + m_nodes + [e_node]
        if len(set(composite)) != len(composite):
            return False, None

        # If we've gotten here, then we know that this is a valid bubble.
        for ch in chains_to_subsume:
            ch.is_subsumed = True
        return True, composite

class Rope(NodeGroup):
    """A group of nodes collapsed into a Rope."""

    def __init__(self, *nodes):
        """Initializes the Rope, given a list of nodes comprising it."""
        super(Rope, self).__init__('R', config.FRAYEDROPE_STYLE, nodes)
     
    @staticmethod
    def is_valid_rope(s):
        """Returns a 2-tuple of (True, a list of all the nodes in the Rope)
           if a Rope defined with the given start node would be a valid
           Rope. Returns a 2-tuple of (False, None) if such a Rope would be
           invalid.
           
           Assumes s has only 1 outgoing node.
        """
        # Detect the first middle node in the rope
        m1 = s.outgoing_nodes[0]
        # Get all start nodes
        s_nodes = m1.incoming_nodes
        # A frayed rope must have multiple paths from which to converge to
        # the "middle node" section
        if len(s_nodes) < 2: return False, None
        # Ensure none of the start nodes have extraneous outgoing nodes
        # (or have been used_in_collapsing)
        for n in s_nodes:
            if len(n.outgoing_nodes) != 1 or n.used_in_collapsing:
                return False, None
        # Now we know that, regardless of the middle nodes' composition,
        # no chain can exist involving m1 that does not start AT m1.
        # Also we know the start nodes are mostly valid (still need to check
        # that each node in the rope is distinct, but that is done later
        # on after we've identified all middle and end nodes).

        # Check the middle nodes

        # Determine if the middle path of the rope is (or could be) a Chain
        chain_to_subsume = None
        chain_validity, m_nodes = Chain.is_valid_chain(m1)
        if not chain_validity:
            # We could have already grouped the middle nodes of this rope
            # into a chain, which would be perfectly valid
            # (Chain.is_valid_chain() rejects Chains composed of nodes that
            # have already been used in collapsing)
            if m1.used_in_collapsing:
                if type(m1.group) == Chain:
                    m_nodes = m1.group.nodes
                    e_nodes = m_nodes[len(m_nodes) - 1].outgoing_nodes
                    chain_to_subsume = m1.group
                else:
                    # if m1 has been grouped into a pattern that isn't a
                    # chain, don't identify this as a frayed rope
                    return False, None
            # Or we just have a single middle node (assumed if no middle
            # chain exists/could exist)
            else:
                m_nodes = [m1]
                e_nodes = m1.outgoing_nodes
        else:
            # The middle nodes form a chain that has not been "created" yet.
            # This makes this a little easier for us.
            e_nodes = m_nodes[len(m_nodes) - 1].outgoing_nodes
        # Now we have the middle and end nodes of the graph stored.

        # Check ending nodes
        # The frayed rope's converged middle path has to diverge to
        # something for it to be a frayed rope
        if len(e_nodes) < 2: return False, None
        for n in e_nodes:
            # Check for extraneous incoming edges, and that the ending nodes
            # haven't been used_in_collapsing.
            if len(n.incoming_nodes) != 1 or n.used_in_collapsing:
                return False, None
            for o in n.outgoing_nodes:
                # We know now that all of the m_nodes (sans m1) and all of the
                # e_nodes only have one incoming node, but we don't know
                # that about the s_nodes. Make sure that this frayed rope
                # isn't cyclical.
                if o in s_nodes:
                    return False, None

        # Check the entire frayed rope's structure
        composite = s_nodes + m_nodes + e_nodes
        # Verify all nodes in the frayed rope are distinct
        if len(set(composite)) != len(composite):
            return False, None

        # If we've made it here, this frayed rope is valid!
        if chain_to_subsume != None:
            chain_to_subsume.is_subsumed = True
        return True, composite

class Chain(NodeGroup):
    """A group of nodes collapsed into a Chain. This is defined as > 1
       nodes that occur one after the other, with no intermediate edges.
    """
    def __init__(self, *nodes):
        """Initializes the Chain, given all the nodes comprising the chain."""
        super(Chain, self).__init__('C', config.CHAIN_STYLE, nodes);

    @staticmethod
    def is_valid_chain(s):
        """Returns a 2-tuple of (True, a list of all the nodes in the Chain
           in order from start to end) if a Chain defined at the given start
           node would be valid. Returns a 2-tuple of (False, None) if such a
           Chain would be considered invalid.
           
           Note that this finds the longest possible Chain that includes s,
           if a Chain exists starting at s. If we decide that no Chain
           exists starting at s then we just return (False, None), but if we
           find that a Chain does exist starting at s then we traverse
           "backwards" to find the longest possible chain including s.
        """
        if len(s.outgoing_nodes) != 1:
            return False, None
        # Determine the composition of the Chain (if one exists starting at s)
        # First, check to make sure we have the minimal parts of a Chain:
        # a starting node with one outgoing edge to another node, and the other
        # node only has one incoming edge (from the starting node). The other
        # node also cannot have an outgoing edge to the starting node.
        if s.outgoing_nodes[0] == s or type(s.outgoing_nodes[0]) != Node:
            return False, None
        chain_list = [s]
        curr = s.outgoing_nodes[0]
        chain_ends_cyclically = False
        # We iterate "down" through the chain.
        while True:
            if (len(curr.incoming_nodes) != 1 or type(curr) != Node
                                            or curr.used_in_collapsing):
                # The chain has ended, and this can't be the last node in it
                # (The node before this node, if applicable, is the chain's
                # actual end.)
                break
            
            if len(curr.outgoing_nodes) != 1:
                # Like above, this means the end of the chain...
                # NOTE that at this point, if curr has an outgoing edge to a
                # node in the chain list, it has to be to the starting node.
                # This is because we've already checked every other node in
                # the chain list to ensure that every non-starting node has
                # only 1 incoming node.
                if len(curr.outgoing_nodes) > 1 and s in curr.outgoing_nodes:
                    chain_ends_cyclically = True
                else:
                    # ...But this is still a valid end-node in the chain.
                    chain_list.append(curr)
                # Either way, we break -- we're done traversing the chain
                # forwards.
                break

            # See above NOTE re: cyclic outgoing edges. This is basically
            # the same thing.
            if curr.outgoing_nodes[0] == s:
                chain_ends_cyclically = True
                break

            # If we're here, the chain is still going on!
            chain_list.append(curr)
            curr = curr.outgoing_nodes[0]

        # Alright, done iterating down the chain.
        if len(chain_list) <= 1 or chain_ends_cyclically:
            # There wasn't a Chain starting at s. (There might be a Chain
            # that includes s that starts "before" s, but we don't really
            # bother with that now -- we only care about optimality when
            # reporting that a Chain exists. We would find such a Chain later,
            # anyway.)
            # Also, re chain_ends_cyclically:
            # We'll detect a cycle here when we're actually looking for
            # cycles -- so don't count this as a chain.
            return False, None

        if len(s.incoming_nodes) != 1:
            # s was already the optimal starting node, so just return what we
            # have currently
            return True, chain_list

        # If we're here, we know a Chain exists starting at s. Can it be
        # extended in the opposite direction to start at a node "before" s?
        # We run basically what we did above, but in reverse.
        backwards_chain_list = []
        curr = s.incoming_nodes[0]
        while True:
            if (len(curr.outgoing_nodes) != 1 or type(curr) != Node
                                            or curr.used_in_collapsing):
                # The node "before" this node is the optimal starting node.
                # This node can't be a part of the chain.
                break
            if len(curr.incoming_nodes) != 1:
                # This indicates the end of the chain, and this is the optimal
                # starting node in the chain.
                if len(set(curr.incoming_nodes) & set(chain_list)) > 0:
                    # Chain "begins" cyclically, so we'll tag it as a cycle
                    # when detecting cycles
                    return False, None
                backwards_chain_list.append(curr)
                break
            # The backwards chain continues. Fortunately, if the chain had
            # invalid references (e.g. last node has an outgoing edge to the
            # prior start node or something), those should have been caught
            # in the forwards chain-checking, so we don't need to check for
            # that corner case here.
            backwards_chain_list.append(curr)
            curr = curr.incoming_nodes[0]
        if backwards_chain_list == []:
            # There wasn't a more optimal starting node -- this is due to the
            # node "before" s either not being a Node, or having > 1 outgoing
            # edges.
            return True, chain_list
        # If we're here, we found a more optimal starting node
        backwards_chain_list.reverse()
        return True, backwards_chain_list + chain_list

class Cycle(NodeGroup):
    """A group of nodes collapsed into a Cycle. This is defined as > 1
       nodes that occur one after another with no intermediate edges, where
       the sequence of nodes repeats.
       
       (Less formally, this is essentially a Chain where the 'last' node has
       one outgoing edge to the 'first' node.
    """
    def __init__(self, *nodes):
        """Initializes the Cycle, given all the nodes comprising it."""
        super(Cycle, self).__init__('Y', config.CYCLE_STYLE, nodes)

    @staticmethod
    def is_valid_cycle(s):
        """Identifies the simple cycle that "starts at" a given starting
           node, if such a cycle exists. Returns (True, [nodes]) if
           such a cycle exists (where [nodes] is a list of all the nodes in
           the cycle), and (False, None) otherwise.
           
           NOTE that this only identifies cycles without any intermediate
           incoming/outgoing edges not in the simple cycle -- that is, this
           basically just looks for chains that end cyclically. (This also
           identifies single-node loops as cycles.)
           
           The ideal way to implement cycle detection in a graph is to use
           Depth-First Search (so, in our case, it would be to modify the
           code in collate.py that already runs DFS to identify cycles), but
           for now I think this more limited-in-scope method should work ok.
        """
        s_outgoing_node_ct = len(s.outgoing_nodes)
        if len(s.incoming_nodes) == 0 or s_outgoing_node_ct == 0:
            # If s has no incoming or no outgoing nodes, it can't be in
            # a cycle!
            return False, None
        # Edge case: we identify single nodes with loops to themselves.
        # If the start node has multiple outgoing edges but no reference to
        # itself, then it isn't the start node for a cycle. (It could very
        # well be the end node of another cycle, but we would eventually
        # test that node for being a cycle later on.)
        if s in s.outgoing_nodes:
            # Valid whether s has 1 or >= 1 outgoing edges
            return True, [s]
        elif s_outgoing_node_ct > 1:
            # Although we allow singleton looped nodes to be cycles (and to
            # have > 1 outgoing nodes), we don't allow larger cycles to be
            # constructed from a start node with > 1 outgoing nodes (since
            # these are chain-like cycles, as discussed above).
            return False, None
        # We iterate "down" through the cycle to determine its composition
        cycle_list = [s]
        curr = s.outgoing_nodes[0]
        while True:
            if (len(curr.incoming_nodes) != 1 or type(curr) != Node
                                            or curr.used_in_collapsing):
                # The cycle has ended, and this can't be the last node in it
                # (The node before this node, if applicable, is the cycle's
                # actual end.)
                return False, None
            
            if len(curr.outgoing_nodes) != 1:
                # Like above, this means the end of the cycle, but it can
                # mean the cycle is valid.
                # NOTE that at this point, if curr has an outgoing edge to a
                # node in the cycle list, it has to be to the starting node.
                # This is because we've already checked every other node in
                # the cycle list to ensure that every non-starting node has
                # only 1 incoming node.
                if len(curr.outgoing_nodes) > 1 and s in curr.outgoing_nodes:
                    return True, cycle_list + [curr]
                else:
                    # If we didn't loop back to start at the end of the
                    # cycle, we never will for this particular cycle. So
                    # just return False.
                    return False, None

            # We know curr has one incoming and one outgoing edge. If its
            # outgoing edge is to s, then we've found a cycle.
            if curr.outgoing_nodes[0] == s:
                return True, cycle_list + [curr]

            # If we're here, the cycle is still going on -- the next node to
            # check is not already in the cycle_list.
            cycle_list.append(curr)
            curr = curr.outgoing_nodes[0]

        # If we're here then something went terribly wrong

class Component(object):
    """A connected component in the graph. We use this in order to
       maintain meta-information, such as node groups, for each connected
       component we're interested in.
    """
    def __init__(self, node_list, node_group_list):
        """Given a list of all nodes (i.e. not node groups) and a list of
           all node groups in the connected component, intializes the
           connected component.
        """
        self.node_list = node_list
        self.node_group_list = node_group_list 

    def node_and_edge_info(self):
        """Returns the node and edge info for this connected component
           as a 2-string tuple, where the first string is node info and the
           second string is edge info (and both strings are DOT-compatible).
        """

        node_info = ""
        edge_info = ""
        # Get node info from groups (contains info about the group's child
        # nodes as well)
        for g in self.node_group_list:
            node_info += g.node_info()

        # Get node info from "standalone nodes" (not in node groups)
        # Simultaneously, we get edge info from all nodes, standalone or not
        # (GraphViz will reconcile this edge information with the node group
        # declarations to specify where edges should be in the xdot file)
        for n in self.node_list:
            if not n.used_in_collapsing:
                node_info += n.node_info()
            edge_info += n.edge_info()

        return node_info, edge_info

    def __repr__(self):
        """Returns a (somewhat verbose) string representation of this
           component.
        """
        return "Component of " + str(self.node_list) + \
                "; " + str(self.node_group_list)
