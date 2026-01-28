from .. import ui_utils, config
from metagenomescope.errors import WeirdError, GraphParsingError


def get_only_connecting_edge_uid(g, src_id, tgt_id):
    """Gets the "uid" attribute of the only edge between two nodes.

    Raises an error if there is not exactly one edge between these two nodes.

    Parameters
    ----------
    g: nx.MultiDiGraph
    src_id: int
    tgt_id: int
    """
    adj = g.adj[src_id]
    suffix = f"from node ID {src_id} to node ID {tgt_id}"
    if tgt_id not in adj:
        raise WeirdError(f"0 edges {suffix}")
    if len(adj[tgt_id]) > 1:
        raise WeirdError(f"> 1 edge {suffix}")
    return g.edges[src_id, tgt_id, 0]["uid"]


def validate_nonempty(ag):
    """Raises an error if an AssemblyGraph has 0 nodes and/or edges.

    We allow node-centric graphs to have 0 edges (so long as they have at
    least one node), but edge-centric graphs must have at least one edge
    (implying at least one node).
    """
    if ag.node_centric:
        if ag.node_ct == 0:
            raise GraphParsingError("Graph has 0 nodes.")
    else:
        # NOTE: the DOT parsing function already checks for this, so it
        # is impossible (well, not really, it's just a pain) to test these
        # branches of this function. I am leaving them in as failsafes.
        if ag.edge_ct == 0:
            raise GraphParsingError("Graph has 0 edges.")
        if ag.node_ct == 0:
            # if we make it here, the graph has >= 1 edge but 0 nodes.
            # um. that's not a graph any more i think
            raise WeirdError("Get thee behind me, satan")


def validate_multiple_ccs(ag):
    """Raises an error if an AssemblyGraph contains <= 1 components.

    Of course it is okay for a graph to have only 1 component, but this
    function is intended to be called after we have already observed that
    it contains multiple components -- it's just a sanity check.
    """
    if len(ag.components) == 1:
        raise WeirdError("Graph has only a single component")
    elif len(ag.components) < 1:
        raise WeirdError("Graph has < 1 components? Something is busted.")


def get_treemap_rectangles(cc_nums, node_ct, aggregate=True):
    """Formats components of a given node size to be represented in a treemap.

    Parameters
    ----------
    cc_nums: list of int
        List of component size ranks that all contain a given number of nodes.
        Because of the way component size ranks are produced (by sorting
        components based first on how many nodes they contain), this should
        be a continuous range. It is okay if this list contains only a single
        component size rank; this indicates that just one component contains
        node_ct nodes.

    node_ct: int
        The number of nodes that each component in cc_nums contains.

    aggregate: bool
        If True, we will only create a single rectangle (representing all of
        these components). Otherwise, we will create one rectangle for each
        component.

    Returns
    -------
    names, sizes: list of str, list of int
        "names" describes the name of each rectangle. If len(cc_nums) > 1 and
        aggregate=True, then this will be formatted in a fancy way to indicate
        that this rectangle represents multiple components.

        "sizes" describes the size of each rectangle, in terms of nodes.

        Note that, if aggregate=True, then len(names) == len(sizes) == 1.
        (Either this is because multiple components will be aggregated
        together -- if len(cc_nums) > 1 -- or it is because len(cc_nums) == 1.)

    Raises
    ------
    WeirdError
        If len(cc_nums) < 1.
        If aggregate=True and cc_nums does not represent a continuous range
        of integers.
    """
    if len(cc_nums) < 1:
        raise WeirdError("cc_nums cannot be empty")
    names = []
    sizes = []
    if len(cc_nums) > 1 and aggregate:
        min_cc_num = min(cc_nums)
        max_cc_num = max(cc_nums)
        # NOTE: now that we delegate computing the hover text template to
        # ui_utils.fmt_num_ranges(), this is no longer a strict requirement;
        # that function can describe discontinuous cc size ranks. However, we
        # should not see this happen in practice here, so let's be paranoid.
        if max_cc_num - min_cc_num + 1 != len(cc_nums):
            raise WeirdError(
                "Discontinuous size ranks: "
                f"|{min_cc_num:,} to {max_cc_num:,}| != {len(cc_nums):,}"
            )
        names.append(
            f"{ui_utils.fmt_num_ranges(cc_nums)} ({node_ct:,}-node components)"
        )
        # If we have let's say 5 components that each contain
        # exactly 3 nodes, then they represent 15 nodes total.
        sizes.append(node_ct * len(cc_nums))
    else:
        for cc_num in sorted(cc_nums):
            names.append(f"#{cc_num:,}")
            sizes.append(node_ct)
    return names, sizes


def validate_split_type(split):
    if split not in (config.SPLIT_LEFT, config.SPLIT_RIGHT, None):
        raise WeirdError(f"Invalid split type: {split}")


def get_sorted_subgraphs(sgs):
    # The number of "full" nodes (i.e. ignoring node splitting) MUST be the
    # highest-priority sorting criterion. Otherwise, we will be unable to
    # say that an aggregated group of components with the exact same
    # amount of nodes represents a continuous range of component size
    # ranks. See the treemap plot code.
    return sorted(
        sgs,
        key=lambda obj: (
            obj.num_full_nodes,
            obj.num_total_nodes,
            obj.num_total_edges,
            obj.pattern_stats.sum(),
        ),
        reverse=True,
    )
