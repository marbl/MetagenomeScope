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


# If you try to run "from . import Node" then python explodes and complains
# about circular imports. little known programming fact: this is actually
# because god hates me personally!
from .node import Node
from .pattern_stats import PatternStats
from metagenomescope import config, cy_config, misc_utils
from metagenomescope.errors import WeirdError


def get_ids_of_nodes(nodes):
    return [n.unique_id for n in nodes]


def verify_vr_and_nodes_good(vr, nodes):
    """Checks a Pattern's ValidationResults object and Node objects.

    Verifies that:
    (1) the ValidationResults describes a valid pattern,
    (2) all Nodes in "nodes" have unique IDs (at least compared to each other),
    and
    (3) vr.nodes exactly matches "nodes".
    """
    if not vr:
        raise WeirdError(
            "Can't create a Pattern from an invalid ValidationResults?"
        )

    # We only verify that the IDs described by the Nodes in "nodes" are unique
    # -- the ValidationResults constructor should have already verified that
    # its .nodes are unique.
    node_ids = get_ids_of_nodes(nodes)
    misc_utils.verify_unique(node_ids)

    if set(node_ids) != set(vr.node_ids):
        raise WeirdError(f"Different node IDs: {node_ids} vs. {vr.node_ids}")


def verify_edges_in_induced_subgraph(edges, node_ids):
    for e in edges:
        if e.dec_src_id not in node_ids or e.dec_tgt_id not in node_ids:
            raise WeirdError(
                f"{e} not in induced subgraph of node IDs {node_ids}?"
            )


def verify_1_node(node_ids, node_type):
    if len(node_ids) != 1:
        raise WeirdError(f"Not exactly 1 {node_type} node: {node_ids}?")


class Pattern(Node):
    """Represents a pattern in an assembly graph."""

    def __init__(
        self,
        unique_id,
        validation_results,
        nodes,
        edges,
    ):
        """Initializes this Pattern object.

        Parameters
        ----------
        unique_id: int
            Unique (with respect to all other nodes, edges, and patterns in
            the assembly graph) integer ID of this pattern.

        validation_results: validators.ValidationResults
            Results from successfully validating this pattern in the assembly
            graph.

        nodes: list of Nodes
            List of all child Node objects of this pattern (including collapsed
            Patterns -- note that Pattern is a subclass of Node!). The IDs of
            these Nodes should exactly match those in
            validation_results.node_ids.

        edges: list of Edges
            List of all child Edge objects of this pattern. We define an edge
            as a child of a pattern P if both its source and target node are
            contained in "nodes". (You can therefore think of "edges" as the
            edges of the "induced subgraph" of "nodes".)
        """
        self.unique_id = unique_id

        verify_vr_and_nodes_good(validation_results, nodes)
        self.pattern_type = validation_results.pattern_type
        self.start_node_ids = validation_results.start_node_ids
        self.end_node_ids = validation_results.end_node_ids

        self.nodes = nodes
        verify_edges_in_induced_subgraph(edges, validation_results.node_ids)
        self.edges = edges

        # Update parent ID info for child nodes (including patterns) and edges
        self.merged_child_chains = []
        is_chain_ish = (
            self.pattern_type == config.PT_CHAIN
            or self.pattern_type == config.PT_CYCLICCHAIN
        )
        self.has_compound_child_nodes = False
        # Iterate through a copy of self.nodes, since we may remove merged
        # chain nodes from self.nodes (and removing from a list while iterating
        # through it will cause weird behavior).
        for node in self.nodes[:]:
            node.parent_id = self.unique_id
            if node.compound:
                self.has_compound_child_nodes = True
                if is_chain_ish and node.pattern_type == config.PT_CHAIN:
                    self._absorb_child_pattern(node)
        for edge in self.edges:
            edge.parent_id = self.unique_id

        # we'll set this later, after pattern detection
        self.cc_num = None

        # This is the shape used for this pattern during layout. In the actual
        # end visualization we might use different shapes for collapsed
        # patterns (e.g. hexagons for bubbles, hourglasses for frayed ropes),
        # but these should take up space that is a subset of the space taken up
        # by the rectangle, so just using a rectangle for layout should be ok.
        self.shape = "rectangle"

        name = f"{config.PT2HR_NOSPACE[self.pattern_type]}{self.unique_id}"
        # Use the Node constructor to initialize the rest of the stuff we need
        super().__init__(unique_id, name, {}, compound=True)

    def __repr__(self):
        return (
            f"{self.name} containing "
            f"nodes {self.get_node_ids()} from {self.start_node_ids} to "
            f"{self.end_node_ids}"
        )

    def pretty_print(self, indent=""):
        innerindent = indent + "  "

        def add(out, nametext):
            if len(out) > 0:
                return out + f",\n{innerindent}" + nametext
            else:
                return out + nametext

        nn = ""
        sn = ""
        en = ""
        for n in self.nodes:
            if n.compound:
                p = n.pretty_print(innerindent)
            else:
                p = n.name
            nn = add(nn, p)
            if n.unique_id in self.start_node_ids:
                sn = add(sn, p)
            # currently we should never have a node be both the start and end
            # of the same pattern, but let's future proof this and allow it
            if n.unique_id in self.end_node_ids:
                en = add(en, p)
        return (
            f"{self.name} of {{\n"
            f"{innerindent}{nn}\n"
            f"{innerindent}---from---\n"
            f"{innerindent}{sn}\n"
            f"{innerindent}----to----\n"
            f"{innerindent}{en}\n"
            f"{indent}}}"
        )

    def _absorb_child_pattern(self, child_pattern):
        """Merges a child Pattern's contents into this Pattern.

        As of writing, this should only be applied if child_pattern is a chain
        (and this Pattern, i.e. "self," is a chain or cyclic chain).

        Note that this method has no conception of the AssemblyGraph in which
        these Patterns are contained: we leave it up to the caller to reroute
        edges.
        """
        # (This attr is set to False by default in the Node constructor)
        child_pattern.removed = True
        # Note that we should only need to go one level down -- this is because
        # the "absorption" process, if applicable, is done as soon as we create
        # a new Pattern. So we don't have to check e.g. the grandchildren, if
        # present, of this pattern. (I guess we could do this all at once at
        # the end of pattern detection, maybe? might be problematic tho.)
        for node in child_pattern.nodes:
            node.parent_id = self.unique_id
            self.nodes.append(node)
        for edge in child_pattern.edges:
            edge.parent_id = self.unique_id
            self.edges.append(edge)

        # there should never be a case where a node is both the start
        # and end of this new pattern, but let's be safe anyway
        verify_1_node(self.start_node_ids, "start")
        verify_1_node(self.end_node_ids, "end")
        verify_1_node(child_pattern.start_node_ids, "start")
        verify_1_node(child_pattern.end_node_ids, "end")
        if self.start_node_ids[0] == child_pattern.unique_id:
            self.start_node_ids = [child_pattern.start_node_ids[0]]
        if self.end_node_ids[0] == child_pattern.unique_id:
            self.end_node_ids = [child_pattern.end_node_ids[0]]

        self.nodes.remove(child_pattern)
        self.merged_child_chains.append(child_pattern)

    def get_node_ids(self):
        return get_ids_of_nodes(self.nodes)

    def make_into_split(self):
        raise WeirdError(f"Attempted to split Pattern {self}.")

    def get_descendant_info(self):
        """Returns descendant Node, Edge, and Pattern objs (and PatternStats).

        Note that we include this object in the returned list of Pattern
        objects, and in the returned PatternStats.

        Returns
        -------
        list of Nodes, list of Edges, list of Patterns, PatternStats
        """
        nodes = []
        edges = []
        patts = [self]
        patt_stats = PatternStats()
        patt_stats.update(self.pattern_type)
        for node in self.nodes:
            if node.compound:
                pn, pe, pp, ps = node.get_descendant_info()
                nodes.extend(pn)
                edges.extend(pe)
                patts.extend(pp)
                patt_stats += ps
            else:
                nodes.append(node)
        for edge in self.edges:
            edges.append(edge)
        return nodes, edges, patts, patt_stats

    def flatten_child_edges(self):
        """Flatten child edges of certain types of patterns.

        For config.PT2FLATTEN_CHILD_EDGES, see config.py -- it has some
        explanations for types of patterns are included there.

        The stuff for bubbles and frayed ropes here is mostly due to the fact
        that edge ports are now on by default. This is, of course, kind of
        handwavy and subject to change if I end up making the Graphviz ->
        Cytoscape.js edge conversion stuff look nicer for simple structures.
        I dunno, as of August 2026 I feel like the curvy lines you see on
        simple bubbles and frayed ropes look a bit ugly? But they look nice
        for more complex versions of these structures!
        """
        if config.PT2FLATTEN_CHILD_EDGES[self.pattern_type]:
            return True
        elif self.pattern_type == config.PT_BUBBLE:
            # simple 4-node, 4-edge bubbles where none of the child nodes
            # are collapsed patterns. Note that although 3-node bubbles are
            # technically even simpler, Graphviz likes to position the nodes
            # in such a way that drawing the edges with straight lines only
            # will look bad -- e.g.
            #
            #  /---------\
            # 0 --> 1 --> 2
            return (
                not self.has_compound_child_nodes
                and len(self.nodes) == 4
                and len(self.edges) == 4
            )
        elif self.pattern_type == config.PT_FRAYEDROPE:
            # Simple frayed ropes (note that at least as of writing all frayed
            # ropes should have at least 5 nodes, so this is really only
            # relevant to the super simple case).
            #
            # We don't check if any of the child nodes are collapsed patterns,
            # since that should only impact the middle node of the frayed rope
            # and that shouldn't impact the "need" for drawing fancy edges imo.
            return len(self.nodes) == 5
        return False

    def to_cyjs(self):
        """Creates a Cytoscape.js element for this pattern.

        Note that we don't do this recursively; we assume that the caller
        already knows about all nodes and edges in this pattern. So, we just
        return a single Cytoscape.js element representing this pattern.
        """
        ele = {
            "data": {
                "id": str(self.unique_id),
                # this lets us distinguish between patterns and "normal" nodes
                "ntype": cy_config.PATTERN_DATA_TYPE,
                "label": config.PT2HR[self.pattern_type],
            },
            "classes": f"pattern {config.PT2HR_NOSPACE[self.pattern_type]}",
        }
        if self.parent_id is not None:
            ele["data"]["parent"] = str(self.parent_id)
        return ele
