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
    # neither of the following cases should ever happen, since this
    # callback should only be triggered on graphs with > 1 components
    if len(ag.components) < 1:
        raise WeirdError("Graph has < 1 components? Something is busted.")
    elif len(ag.components) == 1:
        raise WeirdError("Graph has only a single component")


def get_treemap_rectangles(cc_nums, node_ct, aggregate=True):
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
