from .. import config
from .basic_objects import Edge, NodeGroup
import uuid
import pygraphviz


class SPQRMetaNode(NodeGroup):
    """A group of nodes collapsed into a metanode in a SPQR tree.

       We use OGDF (via the SPQR script) to construct SPQR trees. That
       particular implementation of the algorithm for construction does not
       create "Q" nodes, so the only possible types of metanodes we'll identify
       are S, P, and R metanodes.

       For some high-level background on SPQR trees, Wikipedia is a good
       resource -- see https://en.wikipedia.org/wiki/SPQR_tree. For details on
       the linear-time implementation used in OGDF, see
       http://www.ogdf.net/doc-ogdf/classogdf_1_1_s_p_q_r_tree.html#details.
    """

    def __init__(
        self, bicomponent_id, spqr_id, metanode_type, nodes, internal_edges
    ):
        # Matches a number in the filenames of component_*.info and spqr*gml
        self.bicomponent_id = int(bicomponent_id)
        # Will be updated after the parent Bicomponent of this object has been
        # initialized: the parent bicomponent of this node
        self.parent_bicomponent = None
        # The ID used in spqr*.gml files to describe the structure of the tree
        self.spqr_id = spqr_id
        self.metanode_type = metanode_type
        self.internal_edges = internal_edges
        # Used to maintain a list of edges we haven't reconciled with fancy
        # Edge objects yet (see layout_isolated() in this class)
        self.nonlaidout_edges = internal_edges[:]
        unique_id = str(uuid.uuid4()).replace("-", "_")
        super(SPQRMetaNode, self).__init__(
            self.metanode_type, nodes, spqr_related=True, unique_id=unique_id
        )

    def assign_implicit_spqr_borders(self):
        """Uses this metanode's child nodes' positions to determine
           the left/right/bottom/top positions of this metanode in the
           implicit SPQR decomposition mode layout.
        """
        for n in self.nodes:
            hw_pts = config.POINTS_PER_INCH * (n.width / 2.0)
            hh_pts = config.POINTS_PER_INCH * (n.height / 2.0)
            il = n.parent_spqrnode2relpos[self.parent_bicomponent][0] - hw_pts
            ib = n.parent_spqrnode2relpos[self.parent_bicomponent][1] - hh_pts
            ir = n.parent_spqrnode2relpos[self.parent_bicomponent][0] + hw_pts
            it = n.parent_spqrnode2relpos[self.parent_bicomponent][1] + hh_pts
            if self.xdot_ileft is None or il < self.xdot_ileft:
                self.xdot_ileft = il
            if self.xdot_iright is None or ir > self.xdot_iright:
                self.xdot_iright = ir
            if self.xdot_ibottom is None or ib < self.xdot_ibottom:
                self.xdot_ibottom = ib
            if self.xdot_itop is None or it > self.xdot_itop:
                self.xdot_itop = it

    def layout_isolated(self):
        """Similar to NodeGroup.layout_isolated(), but with metanode-specific
           stuff.
        """
        # pipe .gv into pygraphviz to lay out this node group
        gv_input = ""
        gv_input += "graph metanode {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        gv_input += '\toverlap="scalexy";\n'
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        # We don't pass in edge style info (re: ports) because these edges are
        # undirected
        gv_input += self.node_info(backfill=False)
        for e in self.internal_edges:
            if e[0] == "v":
                # Virtual edge
                gv_input += "\t%s -- %s [style=dotted];\n" % (e[1], e[2])
            else:
                # Real edge
                gv_input += "\t%s -- %s;\n" % (e[1], e[2])
        gv_input += "}"
        cg = pygraphviz.AGraph(gv_input)
        # sfdp works really well for some of these structures. (we can play
        # around with different layout options in the future, of course)
        cg.layout(prog="sfdp")
        # below invocation of cg.draw() is for debugging (also it looks cool)
        # cg.draw("%s.png" % (self.gv_id_string))
        # Obtain cluster width and height from the layout
        bounding_box_text = cg.subgraphs()[0].graph_attr[u"bb"]
        bounding_box_numeric = [float(y) for y in bounding_box_text.split(",")]
        # Expand P metanodes' size; we'll later space out their child nodes
        # accordingly (see issue #228 on the old fedarko/MetagenomeScope
        # GitHub repository).
        if self.metanode_type == "P":
            bounding_box_numeric[2] += 100
        self.xdot_c_width = bounding_box_numeric[2] - bounding_box_numeric[0]
        self.xdot_c_height = bounding_box_numeric[3] - bounding_box_numeric[1]
        # convert width and height from points to inches
        self.xdot_c_width /= config.POINTS_PER_INCH
        self.xdot_c_height /= config.POINTS_PER_INCH
        # Obtain node layout info
        farthest_right_node = None
        for n in cg.nodes():
            curr_node = self.childid2obj[str(n)]
            # Record the relative position (within the node group's bounding
            # box) of this child node.
            ep = n.attr[u"pos"].split(",")
            rel_x = float(ep[0]) - bounding_box_numeric[0]
            if self.metanode_type == "P":
                if farthest_right_node is None or (
                    rel_x > farthest_right_node.parent_spqrnode2relpos[self][0]
                ):
                    farthest_right_node = curr_node
            rel_y = float(ep[1]) - bounding_box_numeric[1]
            curr_node.parent_spqrnode2relpos[self] = [rel_x, rel_y]
        # Space out child nodes in P metanodes, in order to take up the space
        # we added in the metanodes a couple lines earlier in this function
        if self.metanode_type == "P":
            farthest_right_node.parent_spqrnode2relpos[self][0] += 100
        # Obtain edge layout info
        for e in cg.edges():
            self.edge_count += 1
            # technically the distinction btwn. "source" and "target" is
            # meaningless in an undirected graph, but we use that terminology
            # anyway because it doesn't really matter from a layout perspective
            source_id = str(e[0])
            target_id = str(e[1])
            curr_edge = None
            # (self.nonlaidout_edges consists of edge declarations obtained
            # from component_*.info files that have been split(), so when we
            # say en[1:] we're really just obtaining a list of the source ID
            # and target ID for that edge. en[0] defines the type of the edge,
            # either 'v' or 'r'.)
            for en in self.nonlaidout_edges:
                if set(en[1:]) == set([source_id, target_id]):
                    # This edge matches a non-laid-out edge.
                    is_virt = en[0] == "v"
                    curr_edge = Edge(source_id, target_id, is_virtual=is_virt)
                    self.nonlaidout_edges.remove(en)
                    break
            if curr_edge is None:
                raise ValueError("unknown edge obtained from layout")
            self.edges.append(curr_edge)
            # Get control points, then find them relative to cluster dimensions
            (
                ctrl_pt_str,
                coord_list,
                curr_edge.xdot_ctrl_pt_count,
            ) = Edge.get_control_points(e.attr[u"pos"])
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
        if len(self.nonlaidout_edges) > 0:
            raise ValueError(
                "All edges in metanode %s were not laid out"
                % (self.gv_id_string)
            )

    def db_values(self):
        """Returns a tuple containing the values of this metanode, for
           insertion into the .db file.

           Should be called after parsing .xdot layout information for this
           metanode.
        """
        return (
            self.id_string,
            self.component_size_rank,
            self.bicomponent_id,
            len(self.outgoing_nodes),
            self.node_count,
            self.bp,
            self.xdot_left,
            self.xdot_bottom,
            self.xdot_right,
            self.xdot_top,
            self.xdot_ileft,
            self.xdot_ibottom,
            self.xdot_iright,
            self.xdot_itop,
        )


class Bicomponent(NodeGroup):
    """A biconnected component in the graph. We use this to store
       information about the metanodes contained within the SPQR tree
       decomposition corresponding to this biconnected component.

       The process of constructing the "SPQR-integrated" view of the graph is
       relatively involved. Briefly speaking, it involves
       1) Identifying all biconnected components in the assembly graph
       2) Obtaining the SPQR tree decomposition of each biconnected component
       3) Laying out each metanode within a SPQR tree in isolation
       4) Laying out each entire SPQR tree, with metanodes "filled in"
          as solid rectangular nodes (with the width/height determined from
          step 3)
       5) Laying out each connected component of the "single graph," with
          biconnected components "filled in" as solid rectangular nodes (with
          the width/height determined from step 4)
    """

    def __init__(self, bicomponent_id, metanode_list, root_metanode):
        # a string representation of an integer that matches an ID in
        # one component_*.info and one spqr*.gml file
        self.bicomponent_id = bicomponent_id
        self.metanode_list = metanode_list
        self.root_metanode = root_metanode
        # Record this Bicomponent object as a parent of each single node within
        # each metanode.
        self.singlenode_count = 0
        for mn in self.metanode_list:
            # len() is O(1) so this's ok
            self.singlenode_count += len(mn.nodes)
            for n in mn.nodes:
                n.parent_bicomponents.add(self)
            mn.parent_bicomponent = self
        # Get a dict mapping singlenode IDs to their corresponding objects.
        # The length of this dict also provides us with the number of
        # singlenodes contained within this bicomponent when fully implicitly
        # uncollapsed.
        self.snid2obj = {}
        for mn in self.metanode_list:
            # Get a set of singlenodes, since we don't want to include
            # duplicate node info declarations
            for n in mn.nodes:
                self.snid2obj[n.id_string] = n
        # Get a list of real edges contained in the metanodes in this
        # bicomponent.
        self.real_edges = []
        for mn in self.metanode_list:
            for e in mn.internal_edges:
                if e[0] == "r":
                    # This is a real edge
                    self.real_edges.append((e[1], e[2]))
        super(Bicomponent, self).__init__(
            "I",
            self.metanode_list,
            spqr_related=True,
            unique_id=self.bicomponent_id,
        )

    def implicit_backfill_node_info(self):
        """Like calling Bicomponent.node_info(), but using the "implicit"
           decomposition mode dimensions instead of the explicit dimensions.
        """
        return "\tcluster_%s [height=%g,width=%g,shape=rectangle];\n" % (
            self.gv_id_string,
            self.xdot_ic_height,
            self.xdot_ic_width,
        )

    def implicit_layout_isolated(self):
        """Lays out all the singlenodes within this bicomponent, ignoring the
           presence of metanodes in this bicomponent when running layout.

           After that, goes through each metanode to determine its coordinates
           in relation to the singlenodes contained here.
        """
        gv_input = ""
        gv_input += "graph bicomponent {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        gv_input += '\toverlap="scalexy";\n'
        # enclosing these singlenodes/singleedges in a cluster is mostly taken
        # from the NodeGroup.node_info() function, seen above
        gv_input += "subgraph cluster_%s {\n" % (self.gv_id_string)
        if config.GLOBALCLUSTER_STYLE != "":
            gv_input += "\t%s;\n" % (config.GLOBALCLUSTER_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        # Explicitly provide node info first
        # This seems to help a bit with avoiding edge-node crossings
        for n in self.snid2obj.values():
            gv_input += n.node_info()
        for e in self.real_edges:
            gv_input += "\t%s -- %s;\n" % (e[0], e[1])
        gv_input += "}\n}"
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog="sfdp")
        # cg.draw("%s.png" % (self.gv_id_string))
        # Obtain cluster width and height from the layout
        bounding_box_text = cg.subgraphs()[0].graph_attr[u"bb"]
        bounding_box_numeric = [float(y) for y in bounding_box_text.split(",")]
        self.xdot_ic_width = bounding_box_numeric[2] - bounding_box_numeric[0]
        self.xdot_ic_height = bounding_box_numeric[3] - bounding_box_numeric[1]
        # convert width and height from points to inches
        self.xdot_ic_width /= config.POINTS_PER_INCH
        self.xdot_ic_height /= config.POINTS_PER_INCH
        # Obtain node layout info
        for n in cg.nodes():
            curr_node = self.snid2obj[str(n)]
            # Record the relative position (within the node group's bounding
            # box) of this child node.
            ep = n.attr[u"pos"].split(",")
            rel_x = float(ep[0]) - bounding_box_numeric[0]
            rel_y = float(ep[1]) - bounding_box_numeric[1]
            curr_node.parent_spqrnode2relpos[self] = (rel_x, rel_y)
        # Don't even bother getting edge layout info, since we treat all
        # singleedges as straight lines and since we'll be getting edges to put
        # in this bicomponent by looking at the real edges of the metanodes in
        # the tree

    def explicit_layout_isolated(self):
        """Lays out in isolation the metanodes within this bicomponent by
           calling their respective SPQRMetaNode.layout_isolated() methods.

           After that, lays out the entire SPQR tree structure defined for this
           Bicomponent, representing each metanode as a solid rectangle defined
           by its xdot_c_width and xdot_c_height properties.
        """
        for mn in self.metanode_list:
            mn.layout_isolated()
        # Most of the rest of this function is copied from
        # NodeGroup.layout_isolated(), with a few changes.
        # To anyone reading this -- sorry the code's a bit ugly. I might come
        # back and fix this in the future to just use the superclass
        # NodeGroup.layout_isolated() method, if time permits.
        gv_input = ""
        gv_input += "digraph spqrtree {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            gv_input += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)
        gv_input += "subgraph cluster_%s {\n" % (self.gv_id_string)
        if config.GLOBALCLUSTER_STYLE != "":
            gv_input += "\t%s;\n" % (config.GLOBALCLUSTER_STYLE)
        for mn in self.metanode_list:
            gv_input += mn.node_info(backfill=True, incl_cluster_prefix=False)
        gv_input += "}\n"
        for n in self.metanode_list:
            gv_input += n.edge_info(constrained_nodes=self.nodes)
        gv_input += "}"
        cg = pygraphviz.AGraph(gv_input)
        cg.layout(prog="dot")
        # cg.draw(self.gv_id_string + ".png")
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
        # Obtain edge layout info
        for e in cg.edges():
            self.edge_count += 1
            source_node = self.childid2obj[str(e[0])]
            curr_edge = source_node.outgoing_edge_objects[str(e[1])]
            self.edges.append(curr_edge)
            # Get control points, then find them relative to cluster dimensions
            (
                ctrl_pt_str,
                coord_list,
                curr_edge.xdot_ctrl_pt_count,
            ) = Edge.get_control_points(e.attr[u"pos"])
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

    def db_values(self):
        """Returns the "values" of this Bicomponent, suitable for inserting
           into the .db file.

           Note that this should only be called after this Bicomponent has
           been laid out in the context of a single connected component.
        """
        return (
            int(self.bicomponent_id),
            self.root_metanode.id_string,
            self.component_size_rank,
            self.singlenode_count,
            self.xdot_left,
            self.xdot_bottom,
            self.xdot_right,
            self.xdot_top,
            self.xdot_ileft,
            self.xdot_ibottom,
            self.xdot_iright,
            self.xdot_itop,
        )
