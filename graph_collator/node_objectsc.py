# Various objects defining a "node" in the generated graph: both individual,
# and as a node representing multiple groups of nodes (as in Bubble, Rope,
# and Chain).

from graph_config import *
from math import log, sqrt

class Node(object):
    """A generic node. Used for representing individual contigs, and as
       the superclass for groups of nodes collapsed into a single node."""

    # Initializes the object. bp is just the number of base pairs; we'll
    # scale it later if we actually decide to draw this node.
    # (We allow the user to pass in either a str or int as the Node ID;
    # this facilitates polymorphism with collapsed groups of Nodes.)
    def __init__(self, id_value, bp, is_complement, use_rc_prefix=True):
        # If True, we use the "flipped" node style
        self.is_complement = is_complement
        if type(id_value) == int:
            self.id_string = str(id_value)
            if self.is_complement and use_rc_prefix:
                self.id_string = 'c' + self.id_string[1:]
        elif type(id_value) == str:
            self.id_string = id_value
        self.bp = bp
        # List of nodes to which this node has an outgoing edge
        self.outgoing_nodes = []
        # List of nodes from which this node has an incoming edge
        self.incoming_nodes = []
        # Flag variables we use to make DFS/finding connected components
        # more efficient (maintaining a list or dict of this info is more
        # expensive than just using attributes, like this)
        self.seen_in_dfs = False
        self.seen_in_ccomponent = False
        self.seen_in_collapsing = False
        # If we decide to subsume a node group into another node group,
        # thus removing the initial node group, we use this flag to
        # mark that node group to not be drawn.
        self.is_subsumed = False
        
    # Calculates the "height" of this node. Returns a 2-tuple of the
    # node height and an int indicating any rounding up/down done
    # (a value of 0 indicates no rounding, positive values indicate rounding
    # down being done, negative values indicate rounding up being done)
    def get_height(self):
        rounding_done = 0
        h = sqrt(log(self.bp, 100))
        hs = h**2
        if hs > MAX_CONTIG_AREA:
            h = MAX_CONTIG_HEIGHT
            rounding_done = 1
        elif hs < MIN_CONTIG_AREA:
            h = MIN_CONTIG_HEIGHT
            rounding_done = -1
        return (h, rounding_done)

    # Returns a string representing this node that can be used in a .dot
    # file for input to GraphViz.
    # You can change custom_shape to give the node a particular shape; by
    # default, this uses BASIC_NODE_SHAPE for "normal" nodes and
    # RCOMP_NODE_SHAPE for "reverse complement" nodes.
    # If custom_style is passed (e.g. as BUBBLE_STYLE or FRAYEDROPE_STYLE)
    # then that style information will be used. By default, nodes that have
    # been rounded up or down in height will use special style information,
    # but custom_style overrides that.
    def node_info(self, custom_shape=None, custom_style=None):
        h, r = self.get_height()
        # We purposely omit node labels in xdot, since they'll be applied
        # anyway in Cytoscape.js and node labels can result in erroneously
        # resized nodes (to contain node labels)
        info = "\t%s [label=\"\",height=%g,width=%g,shape=" % \
                (self.id_string, h, WIDTH_HEIGHT_RATIO * h)
        if custom_shape == None:
            if not self.is_complement:
                info += BASIC_NODE_SHAPE
            else:
                info += RCOMP_NODE_SHAPE
        else:
            info += custom_shape
        if custom_style == None:
            if r > 0:
               info += ',' + ROUNDED_DN_STYLE
            elif r < 0:
               info += ',' + ROUNDED_UP_STYLE
        else:
            info += ',' + custom_style
        info += "];\n"
        return info

    # Adds an outgoing edge from this node to another node, and adds an
    # incoming edge from the other node referencing this node.
    def add_outgoing_edge(self, node2):
        self.outgoing_nodes.append(node2)
        node2.incoming_nodes.append(self)

    # Replaces an outgoing edge to a given node from this node with another
    # outgoing edge to another node. Used when collapsing groups of nodes.
    # Note that this doesn't create an incoming edge on the new_node, and that
    # this calls set() after replacing the edge to ensure that at most
    # one outgoing edge to a given node is present within the list of outgoing
    # nodes.
    def replace_outgoing_edge(self, curr_node, new_node):
        self.outgoing_nodes.remove(curr_node)
        self.outgoing_nodes.append(new_node)
        self.outgoing_nodes = list(set(self.outgoing_nodes))

    # Same thing as above, but with incoming edges
    def replace_incoming_edge(self, curr_node, new_node):
        self.incoming_nodes.remove(curr_node)
        self.incoming_nodes.append(new_node)
        self.incoming_nodes = list(set(self.incoming_nodes))

    # Returns a GraphViz-compatible string containing all information about
    # outgoing edges from this node. Useful for only printing edges relevant
    # to the nodes we're interested in.
    def edge_info(self):
        o = ""
        for m in self.outgoing_nodes:
            o += "\t%s -> %s\n" % (self.id_string, m.id_string)
        return o

    # For debugging -- returns a str representation of this node
    def __repr__(self):
        return "Node %s" % (self.id_string)

class Bubble(Node):
    """A group of nodes collapsed into a Bubble. This consists of one
       node which points to >= 2 "middle" nodes, all of which in turn point
       to one "end" node."""

    # Initializes the Bubble, given a list of nodes comprising it.
    def __init__(self, *nodes):
        self.chain_len = 0
        self.bp = 0
        self.id_string = "B"
        self.nodes = []
        for n in nodes:
            self.chain_len += 1
            self.bp += n.bp
            self.id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
        self.id_string = self.id_string[:-1] # remove last underscore
        super(Bubble, self).__init__(self.id_string, self.bp, False)

    def node_info(self):
        # This is a pretty hack-ish solution. We actually return the node
        # information for all of the components of the bubble, as one string
        # (and stored in a subgraph starting with cluster).
        info = "subgraph cluster_%s {\n" % (self.id_string)
        for n in self.nodes:
            info += n.node_info()
        info += BUBBLE_STYLE + "}\n"
        return info

    # Returns a 2-tuple of True and the nodes comprising the Bubble if a Bubble
    # defined with the given start node is valid.
    # Returns a 2-tuple of (False, None) if the Bubble is invalid.
    # NOTE that this assumes that s has > 1 outgoing edges.
    @staticmethod
    def is_valid_bubble(s):
        if s.seen_in_collapsing: return False, None
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
                if n.seen_in_collapsing:
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
        if e_node.seen_in_collapsing:
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

class Rope(Node):
    """A group of nodes collapsed into a Rope."""

    # Initializes the Rope, given a list of nodes comprising it.
    def __init__(self, *nodes):
        self.chain_len = 0
        self.bp = 0
        self.id_string = "R"
        self.nodes = []
        for n in nodes:
            self.chain_len += 1
            self.bp += n.bp
            self.id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
        self.id_string = self.id_string[:-1] # remove last underscore
        super(Rope, self).__init__(self.id_string, self.bp, False)
     
    def node_info(self):
        # NOTE: Edge info is still stored with the component nodes. When we
        # do DFS, we detect all nodes, including components. (We don't detect
        # ropes/bubbles/chains, because here they don't have any adjacencies.)
        # So we write edge info of component nodes only once, and we do it
        # outside the cluster (so as not to mess things up).
        info = "subgraph cluster_%s {\n" % (self.id_string)
        for n in self.nodes:
            info += n.node_info()
        info += FRAYEDROPE_STYLE + "}\n"
        return info

    # Returns a 2-tuple of (True, a list of all the nodes in the Rope)
    # if a Rope defined with the given start node would be a valid Rope.
    # Returns a 2-tuple of (False, None) if such a Rope would be invalid.
    # Assumes s has only 1 outgoing node.
    @staticmethod
    def is_valid_rope(s):
        # Detect the first middle node in the rope
        m1 = s.outgoing_nodes[0]
        # Get all start nodes
        s_nodes = m1.incoming_nodes
        # A frayed rope must have multiple paths from which to converge to
        # the "middle node" section
        if len(s_nodes) < 2: return False, None
        # Ensure none of the start nodes have extraneous outgoing nodes
        # (or have been seen_in_collapsing)
        for n in s_nodes:
            if len(n.outgoing_nodes) != 1 or n.seen_in_collapsing:
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
            if m1.seen_in_collapsing:
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
            # haven't been seen_in_collapsing.
            if len(n.incoming_nodes) != 1 or n.seen_in_collapsing:
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

class Chain(Node):
    """A group of nodes collapsed into a Chain. This is defined as > 1
       nodes that occur one after the other, with no intermediate edges."""

    # Initializes the Chain, given all the nodes comprising the chain.
    def __init__(self, *nodes):
        self.chain_len = 0
        self.bp = 0
        self.id_string = "C"
        self.nodes = []
        for n in nodes:
            self.chain_len += 1
            self.bp += n.bp
            self.id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
        self.id_string = self.id_string[:-1] # remove last underscore
        super(Chain, self).__init__(self.id_string, self.bp, False)

    def node_info(self):
        info = "subgraph cluster_%s {\n" % (self.id_string)
        for s in self.nodes:
            info += s.node_info()
        info += CHAIN_STYLE + "}\n"
        return info

    # Returns a 2-tuple of (True, a list of all the nodes in the Chain in order
    # from start to end) if a Chain defined at the given start node would be
    # valid. Returns a 2-tuple of (False, None) if such a Chain would
    # be considered invalid.
    # NOTE that this finds the longest possible Chain that includes s.
    @staticmethod
    def is_valid_chain(s):
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
                                            or curr.seen_in_collapsing):
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
                                            or curr.seen_in_collapsing):
                # The node "before" this node is the optimal starting node.
                # This node can't be a part of the chain.
                break
            if len(curr.incoming_nodes) != 1:
                # This indicates the end of the chain, and this is the optimal
                # starting node in the chain.
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

class Cycle(Node):
    """A group of nodes collapsed into a Cycle. This is defined as > 1
       nodes that occur one after another with no intermediate edges, where
       the sequence of nodes repeats.
       
       (Less formally, this is essentially a Chain where the 'last' node has
       one outgoing edge to the 'first' node."""

    # Initializes the Cycle, given all the nodes comprising the chain.
    def __init__(self, *nodes):
        self.cycle_len = 0
        self.bp = 0
        self.id_string = "Y"
        self.nodes = []
        for n in nodes:
            self.cycle_len += 1
            self.bp += n.bp
            self.id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
        self.id_string = self.id_string[:-1] # remove last underscore
        super(Cycle, self).__init__(self.id_string, self.bp, False)

    def node_info(self):
        info = "subgraph cluster_%s {\n" % (self.id_string)
        for s in self.nodes:
            info += s.node_info()
        info += CYCLE_STYLE + "}\n"
        return info

    # Identifies the simple cycle that "starts at" a given starting node, if
    # such a cycle exists. NOTE that this only identifies cycles without any
    # intermediate incoming/outgoing edges not in the simple cycle -- that
    # is, this basically just looks for chains that end cyclically. (This
    # also identifies loops as cycles -- e.g. a node with a loop that is a
    # connected component will be considered a cycle.)
    # The ideal way to implement cycle detection in a graph is to use
    # Depth-First Search (so, in our case, it would be to modify the code
    # that already runs DFS to identify connected components to also
    # identify cycles), but for now I think this method should work alright.
    @staticmethod
    def is_valid_cycle(s):
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
                                            or curr.seen_in_collapsing):
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
       component we're interested in."""

    def __init__(self, node_list, node_group_list):
        """Given a list of all nodes (i.e. not node groups) and a list of
           all node groups in the connected component, intializes the
           connected component."""

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
            if not n.seen_in_collapsing:
                node_info += n.node_info()
            edge_info += n.edge_info()

        return node_info, edge_info

    def __repr__(self):

        return "Component of " + str(self.node_list) + \
                "; " + str(self.node_group_list)
