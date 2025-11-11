def negate_node_id(id_string):
    """Negates a node ID. Literally, this just adds or removes a starting "-".

    Using this function presumes, of course, that a node's "base" ID in an
    unoriented graph doesn't already start with a "-" character -- because
    that'd mess things up.

    This will raise a ValueError if len(id_string) == 0.
    """
    # account for integer IDs. Can be the case in some GML files, at least.
    if type(id_string) is not str:
        id_string = str(id_string)
    if len(id_string) == 0:
        raise ValueError("Can't negate an empty node ID")
    if id_string[0] == "-":
        return id_string[1:]
    else:
        return "-" + id_string
