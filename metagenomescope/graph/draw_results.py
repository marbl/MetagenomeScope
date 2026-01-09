from .. import ui_utils
from ..errors import WeirdError


class DrawResults(object):
    """Represents a collection of Cytoscape.js elements that were just drawn.

    I guess I didn't feel like making AssemblyGraph.to_cyjs() return like
    6 different things lol
    """

    def __init__(
        self, eles=[], nodect=0, edgect=0, pattct=0, nodeids=None, edgeids=None
    ):
        """Initializes this DrawResults object.

        Parameters
        ----------
        eles: list of dict
            Each entry describes an element (a node, edge, or pattern) in the
            graph, in Cytoscape.js-accepted format. See the references below
            for examples on what this format looks like.

        nodect: float
            List of nodes that were drawn. Split nodes are treated as worth
            0.5 of a "full" node.

        edgect: int
            List of edges that were drawn. Fake edges are not included in this
            count.

        pattct: int
            List of patterns that were drawn.

        nodeids: None or list of int
            List of node IDs that were drawn. You only need to include this
            if you are drawing "around" nodes (in which case there is not an
            immediately easy way to figure out which nodes are drawn when we
            go to do stuff like searching).

            Also note that IDs should generally be integers (at least that's
            how the .unique_id properties of Node/Edge/Pattern objects are
            set), but we don't really care here if these are strings or
            whatever. (I mean the caller might care... but if you are, say,
            me writing tests for this and you used strings for all your IDs,
            then whatever.)

        edgeids: None or list of int
            List of edge IDs that were drawn. Same deal as with nodeids.

        Raises
        ------
        WeirdError
            If the node/edge/patt counts sum to something > len(eles).
            (If they are <= len(eles), then this is okay, since these
            counts can undercount len(eles) due to split nodes/fake edges.)

            If only one of {nodeids, edgeids} is given.

        References
        ----------
        https://dash.plotly.com/cytoscape/elements
        https://js.cytoscape.org/#notation/elements-json
        """
        ctsum = nodect + edgect + pattct
        if ctsum > len(eles):
            raise WeirdError(
                f"{len(eles):,} ele(s), but ("
                f"{nodect:,} node(s) + "
                f"{edgect:,} edge(s) + "
                f"{pattct:,} patt(s)) = {ctsum:,}?"
            )
        if nodeids is not None and nodect > len(nodeids):
            raise WeirdError(
                f"nodect = {nodect:,} but {len(nodeids):,} node ID(s) given?"
            )
        if edgeids is not None and edgect > len(edgeids):
            raise WeirdError(
                f"edgect = {edgect:,} but {len(edgeids):,} edge ID(s) given?"
            )
        self.eles = eles
        self.nodect = nodect
        self.edgect = edgect
        self.pattct = pattct
        self.nodeids = nodeids
        self.edgeids = edgeids
        self.check_ids_given()

    def check_ids_given(self):
        """Returns True if IDs are given and False if not.

        Raises an error if only one of (node IDs, edge IDs) is given.
        """
        if self.nodeids is None:
            if self.edgeids is None:
                return False
            else:
                raise WeirdError("Edge IDs but not node IDs given?")
        else:
            if self.edgeids is None:
                raise WeirdError("Node IDs but not edge IDs given?")
            else:
                return True

    def __repr__(self):
        return (
            "DrawResults("
            f"{len(self.eles):,} ele(s) ["
            f"{self.nodect:,} node(s) + "
            f"{self.edgect:,} edge(s) + "
            f"{self.pattct:,} patt(s)], "
            f"{'ids given' if self.check_ids_given() else 'ids not given'})"
        )

    def get_fancy_count_text(self):
        lsum = ui_utils.pluralize(len(self.eles), "ele")
        nsum = ui_utils.pluralize(self.nodect, "node")
        esum = ui_utils.pluralize(self.edgect, "edge")
        psum = ui_utils.pluralize(self.pattct, "pattern")
        asum = f"({nsum}, {esum}, {psum})"
        return lsum, asum

    def __add__(self, other):
        """Adds two DrawResults objects and does some validation."""
        ids_given = self.check_ids_given()
        if ids_given != other.check_ids_given():
            raise WeirdError(
                f"Can't add {self} and {other}: inconsistent ID presence"
            )

        nodeids = edgeids = None
        if ids_given:
            # paranoia!!! this should really never happen. This MIGHT slow
            # things down slightly, but I sincerely doubt it (this should only
            # be triggered as of writing if there are IDs given, which will
            # only happen if you are drawn around nodes, in which case probably
            # there are not a ton of things being drawn anyway). Also actually
            # lol as of writing we only create a single DR object when drawing
            # around so literally this branch should never happen anyway.
            # whatevs
            if set(self.nodeids) & set(other.nodeids):
                raise WeirdError("Shared node IDs?")
            if set(self.edgeids) & set(other.edgeids):
                raise WeirdError("Shared edge IDs?")
            nodeids = self.nodeids + other.nodeids
            edgeids = self.edgeids + other.edgeids

        return DrawResults(
            eles=self.eles + other.eles,
            nodect=self.nodect + other.nodect,
            edgect=self.edgect + other.edgect,
            pattct=self.pattct + other.pattct,
            nodeids=nodeids,
            edgeids=edgeids,
        )
