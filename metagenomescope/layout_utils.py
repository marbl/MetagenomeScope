from . import config


def get_gv_header(graphname="thing"):
    """Returns the header of a DOT language file.

    This will look something like

    "digraph [graphname] {
        [top-level graph attributes];
        [top-level node attributes];
        [top-level edge attributes];"

    ... It's expected that the caller will, you know, add some actual
    node/edge/subgraph data and close out the graph declaration with a }.
    """
    gv_input = "digraph " + graphname + "{\n"
    if config.GRAPH_STYLE != "":
        gv_input += "\t{};\n".format(config.GRAPH_STYLE)
    if config.GLOBALNODE_STYLE != "":
        gv_input += "\tnode [{}];\n".format(config.GLOBALNODE_STYLE)
    if config.GLOBALEDGE_STYLE != "":
        gv_input += "\tedge [{}];\n".format(config.GLOBALEDGE_STYLE)
    return gv_input


def get_control_points(pos):
    """Removes "startp" and "endp" data, if present, from a string definining
    the "pos" attribute (i.e. the spline control points) of an edge object
    in pygraphviz.

    Also replaces all commas in the filtered string with spaces,
    to make splitting the string easier.

    Returns the split list of coordinates, in the format
    [x1, y1, x2, y2, ..., xn, yn], where each coordinate is a float.

    Raises a ValueError if the number of coordinates is not divisible by 2.

    See http://www.graphviz.org/doc/Dot.ref for more information on
    how splines work in GraphViz.
    """
    # Remove startp data
    if pos.startswith("s,"):
        pos = pos[pos.index(" ") + 1 :]
    # remove endp data
    if pos.startswith("e,"):
        pos = pos[pos.index(" ") + 1 :]

    points_str = pos.replace(",", " ")
    coord_list = [float(c) for c in points_str.split()]
    if len(coord_list) % 2 != 0:
        raise ValueError(
            "Invalid GraphViz edge control points: {}".format(pos)
        )
    return coord_list


def shift_control_points(coord_list, left, bottom):
    r"""Given a list of coordinates (e.g. the output of get_control_points()),
    increases each x coordinate in the list by "left" and increases each y
    coordinate in the list by "bottom".

    The purpose for this is altering the control points of edges within a
    pattern -- the control points are positioned relative to the pattern
    containing the edge, so they can be "shifted" by just taking into account
    the left x and bottom y position of the pattern within the top-level
    component layout.

    ^
    |      +-------------+
    |      | /--->3---\  |
    | 1 -> |2          5 |
    |      | \--->4---/  |
    |  left+-------------+
    |      bottom
    |
    (0, 0)------------------------>
    """
    new_coord_list = []
    for i, coord in enumerate(coord_list):
        if i % 2 == 0:
            new_coord_list.append(left + coord)
        else:
            new_coord_list.append(bottom + coord)
    return new_coord_list


def getxy(pos_string):
    """Given a string of the format "x,y", returns floats of x and y."""
    xs, ys = pos_string.split(",")
    return float(xs), float(ys)
