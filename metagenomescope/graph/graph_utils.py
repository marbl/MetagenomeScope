from .. import ui_utils
from metagenomescope.errors import WeirdError


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
        If cc_nums does not represent a continuous range of integers.
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
                "Something weird is up with the size ranks? "
                f"|{min_cc_num:,} to {max_cc_num:,}| != {len(cc_nums):,}"
            )
        names.append(
            f"{ui_utils.fmt_num_ranges(cc_nums)} ({node_ct:,}-node components)"
        )
        # If we have let's say 5 components that each contain
        # exactly 3 nodes, then they represent 15 nodes total.
        sizes.append(node_ct * len(cc_nums))
    else:
        for cc_num in sorted(cc_nums, reverse=True):
            names.append(f"#{cc_num:,}")
            sizes.append(node_ct)
    return names, sizes
