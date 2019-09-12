# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
# This file defines various objects defining nodes, node groups, edges, etc.
# in the graph. We use these objects to simplify the process of storing
# information about the graph, detecting structural patterns in the graph, and
# performing layout.

from math import log
import pygraphviz

from .. import config


class Edge(object):
    """A generic edge, used for storing layout data (e.g. control points)
       and, if applicable for this type of assembly file, biological
       metadata (e.g. multiplicity).
    """

    def __init__(
        self,
        source_id,
        target_id,
        multiplicity=None,
        orientation=None,
        mean=None,
        stdev=None,
        is_virtual=False,
    ):
        """Initializes the edge and all of its attributes."""
        self.source_id = source_id
        self.target_id = target_id
        # Refers to either multiplicity (in LastGraph files) or bundle size (in
        # MetaCarvel's GML files)
        self.multiplicity = multiplicity
        # Used to characterize edges in MetaCarvel's GML files. Can be one of
        # four possible options: "BB", "BE", "EB", or "EE".
        self.orientation = orientation
        # Per Jay: "estimated distance between two contigs if they are part of
        # the same scaffold. If this number is negative, it means that these
        # contigs overlap by that many bases. If it is positive then there
        # exists a gap of that particular size between two contigs."
        # (For MetaCarvel's GML files)
        self.mean = mean
        # For MetaCarvel's GML files. I don't really know what this means
        self.stdev = stdev
        # We'll eventually assign this edge a "thickness" percentage somewhere
        # in the range [0, 1] (the actual process for doing that is in
        # collate.py). This attribute will contain that information.
        self.thickness = 0.5
        # If we calculate Tukey fences for the edge weights in the connected
        # component that this edge is in -- and if this edge is classified as
        # an outlier during that process -- then we'll set this attribute to
        # either -1 (if this edge is a "low" outlier) or 1 (if this edge is a
        # "high" outlier)
        # (if we don't calculate Tukey fences at all, or if we do but this edge
        # isn't classified as an outlier, then we keep this attribute as 0)
        self.is_outlier = 0
        # For if the edge is an "interior" edge of a node group
        self.group = None
        # Will be replaced with the size rank of the connected component to
        # which this edge belongs
        self.component_size_rank = -1
        # Misc. layout data that we'll eventually record here if we decide
        # to lay out the component in which this edge is stored
        self.xdot_ctrl_pt_str = None
        self.xdot_ctrl_pt_count = None
        # used for interior edges in node groups
        self.xdot_rel_ctrl_pt_str = None
        # used for edges inside metanodes in an SPQR tree
        self.is_virtual = is_virtual

    @staticmethod
    def get_control_points(position):
        """Removes "startp" and "endp" data, if present, from a string
           definining the "position" attribute (i.e. the spline control
           points) of an edge object in pygraphviz.

           Also replaces all commas in the filtered string with spaces,
           to make splitting the string easier.

           Returns a 3-tuple of the filtered string, the split list of
           coordinates (in the format [x1, y1, x2, y2, ... , xn, yn] where
           each coordinate is a float), and the number of points specified by
           the coordinate list (equal to the length of the coordinate list
           divided by 2).

           Raises a ValueError if the number of remaining coordinates (i.e.
           the length of the split list to be returned) is not divisible by 2.

           See http://www.graphviz.org/doc/Dot.ref for more information on
           how splines work in GraphViz.
        """
        # Remove startp data
        if position.startswith("s,"):
            position = position[position.index(" ") + 1 :]
        # remove endp data
        if position.startswith("e,"):
            position = position[position.index(" ") + 1 :]
        points_str = position.replace(",", " ")
        coord_list = [float(c) for c in points_str.split()]
        if len(coord_list) % 2 != 0:
            raise ValueError(config.EDGE_CTRL_PT_ERR)
        # Since len(coord_list) is divisible by 2, we know we can take
        # int(len(coord_list) / 2) without losing precision.
        return points_str, coord_list, int(len(coord_list) / 2)

    def db_values(self):
        """Returns a tuple containing the values of this edge.

           The tuple is created to be inserted into the "edges" database
           table.

           Should be called after parsing .xdot layout information for this
           edge.
        """
        group_id = None
        if self.group is not None:
            group_id = self.group.cy_id_string
        return (
            self.source_id,
            self.target_id,
            self.multiplicity,
            self.thickness,
            self.is_outlier,
            self.orientation,
            self.mean,
            self.stdev,
            self.component_size_rank,
            self.xdot_ctrl_pt_str,
            self.xdot_ctrl_pt_count,
            group_id,
        )

    def s_db_values(self):
        """Returns a tuple of the "values" of this Edge, for insertion
           as a single edge contained within a metanode's skeleton in the
           SPQR-integrated graph.

           Should only be called after this edge has been assigned a
           component_size_rank.
        """
        is_virtual_num = 1 if self.is_virtual else 0
        return (
            self.source_id,
            self.target_id,
            self.component_size_rank,
            self.group.id_string,
            is_virtual_num,
        )

    def metanode_edge_db_values(self):
        """Returns a tuple containing the values of this edge,
           relying on the assumption that this edge is an edge between
           metanodes inside a Bicomponent.

           Should be called after parsing .xdot layout info for this edge.
        """
        return (
            self.source_id,
            self.target_id,
            self.component_size_rank,
            self.xdot_ctrl_pt_str,
            self.xdot_ctrl_pt_count,
            self.group.id_string,
        )

    def __repr__(self):
        return "Edge from %s to %s" % (self.source_id, self.target_id)


class Node(object):
    """A generic node. Used for representing individual contigs/scaffolds,
       and as the superclass for groups of nodes.
    """

    def __init__(
        self,
        id_string,
        bp,
        is_complement,
        depth=None,
        gc_content=None,
        label=None,
        is_single=False,
        is_repeat=None,
    ):
        """Initializes the object. bp initially stood for "base pairs," but
           it really just means the length of this node. In single graphs
           that's measured in bp and in double graphs that's measured in nt.

           (Size scaling based on length is done in self.set_dimensions().)
        """
        self.id_string = id_string
        self.bp = bp
        self.logbp = log(self.bp, config.CONTIG_SCALING_LOG_BASE)
        self.depth = depth
        self.gc_content = gc_content
        self.label = label
        # Either 1 (is a repeat), 0 (is not a repeat), or None (not given)
        self.is_repeat = is_repeat
        # If True, we use the "flipped" node style
        self.is_complement = is_complement
        # If True, we draw nodes without direction
        self.is_single = is_single
        # List of nodes to which this node has an outgoing edge
        self.outgoing_nodes = []
        # List of nodes from which this node has an incoming edge
        self.incoming_nodes = []
        # Dict of Edge objects that have this node as a source -- used for
        # storing/reading more detailed edge information, not used for graph
        # traversal. Edge objects are stored as values, and their
        # corresponding key is the sink (target) node ID of the edge.
        # ...e.g. for 1->2, 1->3, 1->4, outgoing_edge_objects would look like
        # {2: Edge(1, 2), 3: Edge(1, 3), 4: Edge(1, 4)}
        self.outgoing_edge_objects = {}
        # Flag variables we use to make DFS/finding connected components
        # more efficient (maintaining a list or dict of this info is more
        # expensive than just using attributes, like this)
        self.seen_in_dfs = False
        self.in_nodes_to_check = False
        self.seen_in_ccomponent = False
        self.used_in_collapsing = False
        # If we decide to subsume a node group into another node group,
        # thus removing the initial node group, we use this flag to
        # mark that node group to not be drawn.
        self.is_subsumed = False
        # When we collapse nodes into a node group, we change this variable
        # to reference the NodeGroup object in question
        self.group = None
        # Used in the case of nodes in an SPQR tree
        # there should be m + 1 entries in this thing, where m = # of metanodes
        # in the SPQR tree that this node is in. The + 1 is for the parent
        # bicomponent of this node.
        self.parent_spqrnode2relpos = {}
        # Indicates the Bicomponent(s) in which this node is present
        self.parent_bicomponents = set()
        # Reference to the "size rank" (1 for largest, 2 for 2nd largest,
        # ...) of the connected component to which this node belongs.
        self.component_size_rank = -1
        # Default relative proportion (in the range 0.0 to 1.0) used for
        # determining the contig's area relative to other contigs in its
        # connected component.
        self.relative_length = 0.5
        # Used when determining how much of the contig's area its long side
        # should take up. Adjusted based on percentiles, relative to other
        # contigs in the connected component.
        self.longside_proportion = config.MID_LONGSIDE_PROPORTION
        # Misc. layout data that we'll eventually record here
        # The width/height attributes are technically slightly altered by
        # Graphviz during its layout process -- they're scaled to the nearest
        # integer point values. However, we preserve the original dimensions
        # for rendering them in the viewer interface.
        self.width = None
        self.height = None
        self.xdot_x = None
        self.xdot_y = None
        self.xdot_shape = None
        # Optional layout data (used for nodes within subgraphs)
        self.xdot_rel_x = None
        self.xdot_rel_y = None
        # Used for nodes in the "implicit" SPQR decomposition mode:
        self.xdot_ix = None
        self.xdot_iy = None

    def set_dimensions(self):
        """Calculates the width and height of this node and assigns them to
           this node's self.width and self.height attributes, respectively.

           NOTE that "height" and "width" are relative to the default vertical
           layout of the nodes (from top to bottom) -- so height refers to the
           long side of the node and width refers to the short side.

           Some things to keep in mind:
           -self.bp has a minimum possible value of 1
           -self.bp has no maximum possible value, although in practice it'll
            probably be somewhere in the billions (at the time of writing this,
            the longest known genome seems to be Paris japonica's, at
            ~150 billion bp -- source:
            https://en.wikipedia.org/wiki/Paris_japonica)
           -It's desirable to have node area proportional to node length
        """

        # Area is based on the relatively-scaled logarithm of contig length
        area = config.MIN_CONTIG_AREA + (
            self.relative_length * config.CONTIG_AREA_RANGE
        )
        # Longside proportion (i.e. the proportion of the contig's area
        # accounted for by its long side) is based on percentiles of
        # contigs in the component
        self.height = area ** self.longside_proportion
        self.width = area / self.height

    def get_shape(self):
        """Returns the shape "string" for this node."""

        if self.is_complement:
            return config.RCOMP_NODE_SHAPE
        elif self.is_single:
            return config.SINGLE_NODE_SHAPE
        else:
            return config.BASIC_NODE_SHAPE

    def node_info(self):
        """Returns a string representing this node that can be used in a .dot
           file for input to GraphViz.
        """
        self.set_dimensions()
        info = "\t%s [height=%g,width=%g,shape=" % (
            self.id_string,
            self.height,
            self.width,
        )
        info += self.get_shape()
        info += "];\n"
        return info

    def add_outgoing_edge(
        self, node2, multiplicity=None, orientation=None, mean=None, stdev=None
    ):
        """Adds an outgoing edge from this node to another node, and adds an
           incoming edge from the other node referencing this node.

           Also adds an Edge with any specified data to this node's
           dict of outgoing Edge objects.
        """
        self.outgoing_nodes.append(node2)
        node2.incoming_nodes.append(self)
        self.outgoing_edge_objects[node2.id_string] = Edge(
            self.id_string,
            node2.id_string,
            multiplicity=multiplicity,
            orientation=orientation,
            mean=mean,
            stdev=stdev,
        )

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
            # Due to short-circuiting, (m in constrained_nodes) is only
            # evaluated when constrained_nodes is not None.
            if (constrained_nodes is None) or (m in constrained_nodes):
                o += "\t%s -> %s\n" % (self.id_string, m.id_string)
        return o

    def collapsed_edge_info(self):
        """Returns a GraphViz-compatible string (like in edge_info()) but:

           -Edges that have a .group attribute of None that point to/from
            nodes that have a .group attribute that is not None will be
            reassigned (in the string) to point to/from those node groups.

           -Edges that have a .group attribute that is not None will not be
            included in the string.

           -All edges will have a comment attribute of the format "a,b" where
            a is the id_string of the original source node of the edge (so,
            not a node group) and b is the id_string of the original target
            node of the edge.
        """
        o = ""
        if self.group is not None:
            source_id = "cluster_" + self.group.gv_id_string
        else:
            source_id = self.id_string
        for m in self.outgoing_nodes:
            # Used to record the actual edge source/target
            comment = '[comment="%s,%s"]' % (self.id_string, m.id_string)
            # Only record edges that are not in a group (however, this
            # includes edges potentially between groups)
            if self.outgoing_edge_objects[m.id_string].group is None:
                if m.group is None:
                    o += "\t%s -> %s %s\n" % (source_id, m.id_string, comment)
                else:
                    o += "\t%s -> %s %s\n" % (
                        source_id,
                        "cluster_" + m.group.gv_id_string,
                        comment,
                    )
        return o

    def set_component_rank(self, component_size_rank):
        """Sets the component_size_rank property of this node and of all
           its outgoing edges.
        """
        self.component_size_rank = component_size_rank
        for e in self.outgoing_edge_objects.values():
            e.component_size_rank = component_size_rank

    def s_db_values(self, parent_metanode=None):
        """Returns a tuple of the "values" of this Node, for insertion
           as a single node (i.e. a node in the SPQR-integrated graph view).

           If parent_metanode is None, then this just returns these values
           with the parent_metanode_id entry set as None. (It's assumed in
           this case that this node is not in any metanodes, and has
           been assigned .xdot_x and .xdot_y values accordingly.)

           Should only be called after this node (and its parent metanode,
           if applicable) have been laid out.
        """
        ix = iy = x = y = 0
        parent_metanode_id = parent_bicmp_id = None
        if parent_metanode is None:
            x = self.xdot_x
            y = self.xdot_y
            ix = self.xdot_ix
            iy = self.xdot_iy
        else:
            # Use the coordinates of the node group in question to obtain
            # the proper x and y coordinates of this node.
            # also, get the ID string of the parent_metanode in question and
            # set p_mn_id equal to that
            relpos = self.parent_spqrnode2relpos[parent_metanode]
            x = parent_metanode.xdot_left + relpos[0]
            y = parent_metanode.xdot_bottom + relpos[1]
            parent_metanode_id = parent_metanode.cy_id_string
            # Use the bicomponent of the parent metanode to deduce which ix/iy
            # positions should be used for this particular row in the database
            # (since a singlenode can be in multiple bicomponents)
            parent_bicmp = parent_metanode.parent_bicomponent
            parent_bicmp_id = parent_bicmp.id_string
            irelpos = self.parent_spqrnode2relpos[parent_bicmp]
            ix = parent_bicmp.xdot_ileft + irelpos[0]
            iy = parent_bicmp.xdot_ibottom + irelpos[1]
        return (
            self.id_string,
            self.label,
            self.bp,
            self.gc_content,
            self.depth,
            self.is_repeat,
            self.component_size_rank,
            x,
            y,
            ix,
            iy,
            self.width,
            self.height,
            parent_metanode_id,
            parent_bicmp_id,
        )

    def db_values(self):
        """Returns a tuple of the "values" of this Node.

           This value will be used to populate the database's "contigs"
           table with information about this node.

           Note that this doesn't really apply to NodeGroups, since they
           don't have most of these attributes defined. I'll define a more
           specific NodeGroup.db_values() function later.

           Also, this shouldn't be called until after this Node's layout
           information has been parsed from an .xdot file and recorded.
           (Unless we're "faking" the layout of this Node's component, in
           which case everything here should be accounted for anyway.)
        """
        # See collate.py for the most up-to-date specifications of how this
        # table is laid out.
        # The "parent cluster id" field can be either an ID or NULL
        # (where NULL denotes no parent cluster), so we decide that here.
        group_id = None
        if self.group is not None:
            group_id = self.group.cy_id_string
        length = self.bp
        return (
            self.id_string,
            self.label,
            length,
            self.gc_content,
            self.depth,
            self.is_repeat,
            self.component_size_rank,
            self.xdot_x,
            self.xdot_y,
            self.width,
            self.height,
            self.xdot_shape,
            group_id,
        )

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

    plural_name = "other_structural_patterns"
    type_name = "Other"

    def __init__(
        self, group_prefix, nodes, spqr_related=False, unique_id=None
    ):
        """Initializes the node group, given all the Node objects comprising
           the node group, a prefix character for the group (i.e. 'F' for
           frayed ropes, 'B' for bubbles, 'C' for chains, 'Y' for cycles),
           and a GraphViz style setting for the group (generally
           from config.py).

           Note that we use two IDs for Node Groups: one with '-'s replaced
           with 'c's (since GraphViz only allows '-' in IDs when it's the
           first character and the other ID characters are numbers), and one
           with the original ID names. The 'c' version is passed into GraphViz,
           and the '-' version is passed into the .db file to be used in
           Cytoscape.js.

           Also, if this NodeGroup has some unique ID, then you can
           pass that here via the unique_id argument. This makes the
           NodeGroup ID's just the group_prefix + the unique_id, instead
           of a combination of all of the node names contained within this
           NodeGroup (this approach is useful for NodeGroups of NodeGroups,
           e.g. Bicomponents).
        """
        self.node_count = 0
        self.edge_count = 0
        self.bp = 0
        self.logbp = 0
        self.gv_id_string = "%s" % (group_prefix)
        self.cy_id_string = "%s" % (group_prefix)
        self.nodes = []
        self.edges = []
        # dict that maps node id_strings to the corresponding Node objects
        self.childid2obj = {}
        for n in nodes:
            self.node_count += 1
            self.bp += n.bp
            self.logbp += n.logbp
            if unique_id is None:
                self.gv_id_string += "%s_" % (n.id_string.replace("-", "c"))
                self.cy_id_string += "%s_" % (n.id_string)
            self.nodes.append(n)
            # We don't do this stuff if the node group in question is a SPQR
            # metanode, since the model of <= 1 node group per node doesn't
            # really hold here
            if not spqr_related:
                n.used_in_collapsing = True
                n.group = self
            self.childid2obj[n.id_string] = n
        if unique_id is None:
            self.gv_id_string = self.gv_id_string[
                :-1
            ]  # remove last underscore
            self.cy_id_string = self.cy_id_string[
                :-1
            ]  # remove last underscore
        self.xdot_c_width = 0
        self.xdot_c_height = 0
        self.xdot_left = None
        self.xdot_bottom = None
        self.xdot_right = None
        self.xdot_top = None
        # Used specifically for Bicomponents/SPQRMetaNodes in the "implicit"
        # SPQR decomposition mode
        self.xdot_ic_width = 0
        self.xdot_ic_height = 0
        self.xdot_ileft = None
        self.xdot_ibottom = None
        self.xdot_iright = None
        self.xdot_itop = None
        if unique_id is not None:
            self.gv_id_string += unique_id
            self.cy_id_string = self.gv_id_string
        super(NodeGroup, self).__init__(self.gv_id_string, self.bp, False)

    def layout_isolated(self):
        """Lays out this node group by itself. Stores layout information in
           the attributes of both this NodeGroup object and its child
           nodes/edges.
        """
        # pipe .gv into pygraphviz to lay out this node group
        gv_input = ""
        gv_input += "digraph nodegroup {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            gv_input += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)
        gv_input += self.node_info(backfill=False)
        for n in self.nodes:
            # Ensure that only the edges that point to nodes that are within
            # the node group are present; ensures layout is restricted to just
            # the node group in question.
            # This works because the edges we consider in the first place all
            # originate from nodes within the node group, so we don't have to
            # worry about edges originating from nodes outside the node group.
            gv_input += n.edge_info(constrained_nodes=self.nodes)
        gv_input += "}"
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog="dot")
        # Obtain cluster width and height from the layout
        bounding_box_text = cg.subgraphs()[0].graph_attr[u"bb"]
        bounding_box_numeric = [float(y) for y in bounding_box_text.split(",")]
        self.xdot_c_width = bounding_box_numeric[2] - bounding_box_numeric[0]
        self.xdot_c_height = bounding_box_numeric[3] - bounding_box_numeric[1]
        # convert width and height from points to inches
        self.xdot_c_width /= config.POINTS_PER_INCH
        self.xdot_c_height /= config.POINTS_PER_INCH
        # Obtain node layout info
        # NOTE: we could iterate over the subgraph's nodes or over the entire
        # graph (cg)'s nodes -- same result, since the only nodes in the graph
        # are in the subgraph.
        for n in cg.nodes():
            curr_node = self.childid2obj[str(n)]
            # Record the relative position (within the node group's bounding
            # box) of this child node.
            ep = n.attr[u"pos"].split(",")
            curr_node.xdot_rel_x = float(ep[0]) - bounding_box_numeric[0]
            curr_node.xdot_rel_y = float(ep[1]) - bounding_box_numeric[1]
            curr_node.xdot_shape = str(n.attr[u"shape"])
        # Obtain edge layout info
        for e in cg.edges():
            self.edge_count += 1
            source_node = self.childid2obj[str(e[0])]
            # NOTE the following line assumes that the standard-mode graph
            # contains no duplicate edges (which should really be the case,
            # but isn't a given right now; see issue #75 for context)
            curr_edge = source_node.outgoing_edge_objects[str(e[1])]
            self.edges.append(curr_edge)
            # Get control points, then find them relative to cluster dimensions
            ctrl_pt_str, coord_list, curr_edge.xdot_ctrl_pt_count = Edge.get_control_points(
                e.attr[u"pos"]
            )
            curr_edge.xdot_rel_ctrl_pt_str = ""
            p = 0
            while p <= len(coord_list) - 2:
                if p > 0:
                    curr_edge.xdot_rel_ctrl_pt_str += " "
                x_coord = coord_list[p] - bounding_box_numeric[0]
                y_coord = coord_list[p + 1] - bounding_box_numeric[1]
                curr_edge.xdot_rel_ctrl_pt_str += str(x_coord)
                curr_edge.xdot_rel_ctrl_pt_str += " "
                curr_edge.xdot_rel_ctrl_pt_str += str(y_coord)
                p += 2
            curr_edge.group = self

    def node_info(self, backfill=True, incl_cluster_prefix=True):
        """Returns a string of the node_info() of this NodeGroup.

           If backfill is False, this works as normal: this node group is
           treated as a subgraph cluster, and all its child information is
           returned.

           If backfill is True, however, this node group is just treated
           as a rectangular normal node. Furthermore, the resulting node
           "definition" line will be prefixed with "cluster_" if
           incl_cluster_prefix is True. (The value of incl_cluster_prefix is
           only utilized if backfill is True.)
        """
        if backfill:
            output = "\t"
            if incl_cluster_prefix:
                output += "cluster_"
            cs = ""
            if config.COLOR_PATTERNS:
                cs = ',style=filled,fillcolor="%s"' % (
                    config.PATTERN2COLOR[self.plural_name]
                )
            output += "%s [height=%g,width=%g,shape=rectangle%s];\n" % (
                self.gv_id_string,
                self.xdot_c_height,
                self.xdot_c_width,
                cs,
            )
            return output
        else:
            info = "subgraph cluster_%s {\n" % (self.gv_id_string)
            if config.GLOBALCLUSTER_STYLE != "":
                info += "\t%s;\n" % (config.GLOBALCLUSTER_STYLE)
            if config.COLOR_PATTERNS:
                info += '\tbgcolor="%s";\n' % (
                    config.PATTERN2COLOR[self.plural_name]
                )
            for n in self.nodes:
                info += n.node_info()
            info += "}\n"
            return info

    def db_values(self):
        """Returns a tuple containing the values associated with this group.
           Should be called after parsing and assigning .xdot bounding box
           values accordingly.
        """
        # Assign "collapsed dimensions"; these are used when the NodeGroup is
        # collapsed in the viewer interface.
        #
        # All that really needs to be done to change this is modifying unc_w
        # and unc_h. Right now the collapsed dimensions are just proportional
        # to the uncollapsed dimensions, but lots of variation is possible.
        #
        # I implemented actual logarithmic+relative scaling for NodeGroups
        # earlier, where they were scaled alongside contigs based on their
        # average-length child contig. Issue #107 on GitHub describes the
        # process of this in detail, if you're interested.
        #
        # (For now, though, I think the current method is generally fine.)
        #
        # NOTE: If we've assigned a relative_length and longside_proportion
        # to this NodeGroup, we can just call self.set_dimensions() here to
        # set its width and height.
        unc_w = (self.xdot_right - self.xdot_left) / config.POINTS_PER_INCH
        unc_h = (self.xdot_top - self.xdot_bottom) / config.POINTS_PER_INCH
        return (
            self.cy_id_string,
            self.bp,
            self.component_size_rank,
            self.xdot_left,
            self.xdot_bottom,
            self.xdot_right,
            self.xdot_top,
            unc_w * config.COLL_CL_W_FAC,
            unc_h * config.COLL_CL_H_FAC,
            self.type_name,
        )
