from .. import misc_utils


class Layout(object):
    """Performs layout on some part of the graph and outputs the results.

    This could reflect the layout of a single pattern, an entire component,
    a subregion of the graph, etc.

    TODO: define some mechanism for adding Layouts? for component tiling.
    """

    def __init__(
        self,
        components=[],
        nodes=[],
        edges=[],
        patterns=[],
        incl_patterns=True,
    ):
        """Initializes this Layout object."""
        verify_at_least_one_nonempty(components, nodes, edges, patterns)
        self.components = components
        self.nodes = nodes
        self.edges = edges
        self.patterns = patterns
        self.incl_patterns = incl_patterns
