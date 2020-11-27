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
            # This is an x position (since the list is [x, y, x, y, ...])
            new_coord_list.append(left + coord)
        else:
            # This is a y position
            new_coord_list.append(bottom + coord)

    # We should have ended on a y position. If we didn't, something is
    # seriously wrong.
    if i % 2 == 0:
        raise ValueError(
            "Non-even number of control points: {}".format(coord_list)
        )
    return new_coord_list


def rotate(x, y):
    """Rotates a position by 90 degrees counterclockwise.

    This is used when converting the graph layout from the top -> bottom
    direction to the left -> right direction.
    """
    return (-y, x)


def rotate_ctrl_pt_coords(coords):
    if len(coords) % 2 != 0:
        raise ValueError("Non-even number of control points")

    # This catches the case where the user passes in [] as coords.
    if len(coords) < 2:
        raise ValueError("Not enough control points given")

    new_coords = []
    for i in range(0, len(coords), 2):
        x, y = coords[i], coords[i + 1]
        newx, newy = rotate(x, y)
        new_coords.append(newx)
        new_coords.append(newy)

    return new_coords


def getxy(pos_string):
    """Given a string of the format "x,y", returns floats of x and y.

    This should implicitly fail if there is not exactly one "," within the
    input string, or if the values on either side are not valid representations
    of numbers.
    """
    xs, ys = pos_string.split(",")
    return float(xs), float(ys)


def get_bb_x2_y2(bb_string):
    """Given a string of the format "x1,y1,x2,y2", returns floats of x2 and y2
    divided by config.POINTS_PER_INCH.

    In a bounding box produced by GraphViz, (x1, y1) is the bottom left
    position of the box and (x2, y2) is the top right position of the box.
    Usually we only care about (x2, y2) (since often the bottom left is just
    (0, 0)), hence this function.

    The reason we divide by POINTS_PER_INCH is because, in GraphViz' output,
    node positions and edge control points are (usually) given in inches,
    whereas bounding boxes are (usually) given in points. To quote Plato,
    "that's kinda annoying tbh." I'm like 90% sure Plato said that once.

    See http://www.graphviz.org/doc/info/attrs.html#d:bb and
    http://www.graphviz.org/doc/info/attrs.html#k:rect for reference.
    """
    x1, y1, x2, y2 = bb_string.split(",")
    x2i = float(x2) / config.POINTS_PER_INCH
    y2i = float(y2) / config.POINTS_PER_INCH
    return x2i, y2i
