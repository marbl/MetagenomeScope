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

    # Initializes the Bubble, given a start node, a list of middle nodes, and
    # an end node.
    def __init__(self, s, middle_nodes, e):
        self.bp = s.bp + e.bp
        self.id_string = "B%s" % (s.id_string)
        # Set each individual node as already_drawn, so we don't draw nodes
        # multiple times accidentally
        for m in middle_nodes:
            self.bp += m.bp
            self.id_string += '_' + m.id_string
        self.id_string += '_' + e.id_string
        # Once we've "combined" the sub-nodes of this Bubble to get their
        # total length (in bp) and a unique ID string, we call the superclass
        # constructor to initialize this object. Not really the cleanest way
        # to go about this, but it should work alright.
        super(Bubble, self).__init__(self.id_string, self.bp, False)
        
        self.start = s
        self.middle_nodes = middle_nodes
        self.end = e

    def node_info(self):
        # This is a pretty hack-ish solution. We actually return the node
        # information for all of the components of the bubble, as one string
        # (and stored in a subgraph starting with cluster).
        info = "subgraph cluster_%s {\n" % (self.id_string)
        info += self.start.node_info()
        for m in self.middle_nodes:
            info += m.node_info()
        info += self.end.node_info()
        info += BUBBLE_STYLE + "}\n"
        return info

    # Returns a 2-tuple of True and the ending node of the Bubble if a Bubble
    # defined with the given start node and middle nodes is valid.
    # (This determines the "end" node of the Bubble by itself.)
    # Returns a 2-tuple of (False, None) if the Bubble is invalid.
    # NOTE that this assumes that s has > 1 outgoing edges.
    @staticmethod
    def is_valid_bubble(s):
        middle_nodes = s.outgoing_nodes
        e = None
        # Verify all "middle" nodes in the Bubble connect to a single end node
        for m in middle_nodes:
            if len(m.outgoing_nodes) == 1 and len(m.incoming_nodes) == 1:
                if e == None:
                    # This is the first "middle node" to be processed
                    e = m.outgoing_nodes[0]
                elif e != m.outgoing_nodes[0]:
                    # Not all of the "middle nodes" have the same ending node.
                    # So this isn't a valid Bubble: return false
                    return False, None
            else:
                return False, None
        # Verify that there's at least some ending node: if the user passes []
        # for middle_nodes, or all of the middle nodes have no outgoing nodes,
        # then this should fail since a bubble needs to converge
        # Also, if the ending node has "extra" incoming nodes (that aren't
        # middle nodes, i.e. they're not connected to the starting node),
        # then this isn't a valid bubble.
        if e == None or set(e.incoming_nodes) != set(middle_nodes):
            return False, None
        # Alright, now we've identified a valid ending node
        composite = [s] + middle_nodes + [e]
        # Verify each node in the Bubble is distinct (since sets have unique
        # elements, we can use them to detect this)
        if len(set(composite)) != len(composite): return False, None
        # Verify each node in the Bubble is a basic Node
        for n in composite:
            if type(n) != Node or n.seen_in_collapsing:
                return False, None
        # Verify the ending node doesn't have an edge connecting it back to any
        # of the other nodes within the Bubble
        for o in e.outgoing_nodes:
            if o == s or o in middle_nodes or o == e:
                return False, None
        return True, e

class Rope(Node):
    """A group of nodes collapsed into a Rope. This is defined as two "start"
       nodes, each of which point to a "middle" node, which points to two
       "end" nodes.""" 

    # Initializes the Rope, given two start nodes, a middle node, and two
    # end nodes.
    def __init__(self, s1, s2, m, e1, e2):
        self.bp = s1.bp + s2.bp + m.bp + e1.bp + e2.bp
        self.id_string = "R%s_%s_%s_%s_%s" % (s1.id_string, s2.id_string, \
                m.id_string, e1.id_string, e2.id_string)
        super(Rope, self).__init__(self.id_string, self.bp, False)

        self.starts = (s1, s2)
        self.middle = m
        self.ends = (e1, e2)

    def node_info(self):
        # This is a pretty hack-ish solution. We actually return the node
        # information for all of the components of the rope, as one string
        # (and stored in a subgraph starting with cluster).
        # NOTE: Edge info is still stored with the component nodes. When we
        # do DFS, we detect all nodes, including components. (We don't detect
        # ropes/bubbles/chains, because here they don't have any adjacencies.)
        # So we write edge info of component nodes only once, and we do it
        # outside the cluster (so as not to mess things up).
        info = "subgraph cluster_%s {\n" % (self.id_string)
        for s in self.starts:
            info += s.node_info()
        info += self.middle.node_info()
        for e in self.ends:
            info += e.node_info()
        info += FRAYEDROPE_STYLE + "}\n"
        return info

    # Returns a 2-tuple of (True, a 5-tuple of all the nodes in the Rope (in
    # order (s1, s2, m, e1, e2))) if a Rope defined with the given middle node
    # would be a valid Rope. Returns a 2-tuple of (False, None) if such a Rope
    # would be invalid. Assumes s has only 1 outgoing node.
    @staticmethod
    def is_valid_rope(s):
        # Determine "middle" node
        m = s.outgoing_nodes[0]
        # Determine all "start" nodes
        rope_start = m.incoming_nodes
        if len(rope_start) != 2: return False, None
        s1, s2 = rope_start
        # Determine all "end" nodes
        rope_end = m.outgoing_nodes
        if len(rope_end) != 2: return False, None 
        e1, e2 = rope_end
        # Now that we've determined all the nodes, we can verify certain things
        # about them
        composite = [s1, s2, m, e1, e2]
        # Verify each node in the Rope is distinct
        # Prevents something weird like one of the starting nodes also being
        # an ending node or something similarly invalid
        if len(set(composite)) != len(composite): return False, None
        # Verify each node in the Rope is a basic Node, not a Bubble/Rope/etc.
        for n in composite:
            if type(n) != Node or n.seen_in_collapsing:
                return False, None
        # Ensure starting nodes each only have one outgoing edge.
        for s in (s1, s2):
            if len(s.outgoing_nodes) != 1:
                return False, None
        # Ensure ending nodes' outgoing edges are not incident upon any of the
        # other nodes within the rope
        for e in (e1, e2):
            for o in e.outgoing_nodes:
                if o == s1 or o == s2 or o == m or o == e1 or o == e2:
                    return False, None
            if len(e.incoming_nodes) != 1:
                return False, None
        # If we've made it this far, a rope constructed of these nodes would
        # be valid.
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
    # NOTE that this 1) assumes s has exactly 1 outgoing edge, and 2) finds the
    # longest possible Chain that includes s.
    @staticmethod
    def is_valid_chain(s):
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
