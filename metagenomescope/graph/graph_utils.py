def get_only_connecting_edge_uid(g, src_id, tgt_id):
    """Gets the "uid" attribute of the only edge between two nodes.

    Raises an error if there is not exactly one edge between these two nodes.
    """
    adj = g.adj[src_id]
    suffix = f"from node ID {src_id} to node ID {tgt_id}"
    if tgt_id not in adj:
        raise WeirdError(f"0 edges {suffix}")
    if len(adj[tgt_id]) > 1:
        raise WeirdError(f"> 1 edge {suffix}")
    return g.edges[src_id, tgt_id, 0]["uid"]
