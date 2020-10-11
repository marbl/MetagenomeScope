from .. import config


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
        self.node_group_ct = len(self.node_group_list)
        # Compute node/edge counts, and total sequence length
        self.node_ct = len(self.node_list)
        edge_ct = 0
        total_length = 0
        for n in self.node_list:
            edge_ct += len(n.outgoing_edge_objects)
            total_length += n.bp
        self.edge_ct = edge_ct
        self.total_length = total_length

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
            edge_info += n.collapsed_edge_info()

        return node_info, edge_info

    def produce_non_backfilled_dot_file(self, output_prefix):
        """Returns a string defining the graph (in DOT format) for the current
        component, but without cluster backfilling (i.e. all clusters are
        included as actual dot clusters, and are thus susceptible for edges
        going through them).
        """

        fcontent = "digraph " + output_prefix + " {\n"
        # TODO abstract graph header generation code to separate function
        if config.GRAPH_STYLE != "":
            fcontent += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            fcontent += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            fcontent += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)

        for n in self.node_list:
            if not n.used_in_collapsing:
                fcontent += n.node_info()
            fcontent += n.edge_info()
        for g in self.node_group_list:
            fcontent += g.node_info(backfill=False)
        fcontent += "}"
        return fcontent

    def produce_non_patterned_dot_file(self, output_prefix):
        """Returns a string defining the graph (in DOT format) for the current
        component, but without any clusters (so all nodes and edges are
        still in the graph, but they aren't encapsulated by any clusters).
        """

        fcontent = "digraph " + output_prefix + " {\n"
        if config.GRAPH_STYLE != "":
            fcontent += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            fcontent += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            fcontent += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)

        for n in self.node_list:
            fcontent += n.node_info()
            fcontent += n.edge_info()
        fcontent += "}"
        return fcontent

    def __repr__(self):
        """Returns a (somewhat verbose) string representation of this
        component.
        """
        return (
            "Component of "
            + str(self.node_list)
            + "; "
            + str(self.node_group_list)
        )
