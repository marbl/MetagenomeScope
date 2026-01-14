from . import layout_config
from .. import config


def get_gv_header(name="g"):
    """Returns the header of a DOT language file.

    This will look something like

    "digraph g {
        [top-level graph attributes];
        [top-level node attributes];
        [top-level edge attributes];"

    ... It's expected that the caller will, you know, add some actual
    node/edge/subgraph data and close out the graph declaration with a }.
    """
    gv_input = "digraph " + name + " {\n"
    if layout_config.GRAPH_STYLE != "":
        gv_input += f"{layout_config.INDENT}{layout_config.GRAPH_STYLE};\n"
    if layout_config.GLOBALNODE_STYLE != "":
        gv_input += (
            f"{layout_config.INDENT}node [{layout_config.GLOBALNODE_STYLE}];\n"
        )
    if layout_config.GLOBALEDGE_STYLE != "":
        gv_input += (
            f"{layout_config.INDENT}edge [{layout_config.GLOBALEDGE_STYLE}];\n"
        )
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
        raise ValueError("Invalid GraphViz edge control points: {pos}")
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
        raise ValueError(f"Non-even number of control points: {coord_list}")
    return new_coord_list


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
    divided by layout_config.PIXELS_PER_INCH.

    In a bounding box produced by GraphViz, (x1, y1) is the bottom left
    position of the box and (x2, y2) is the top right position of the box.
    Usually we only care about (x2, y2) (since often the bottom left is just
    (0, 0)), hence this function.

    The reason we divide by PIXELS_PER_INCH is because, in Graphviz' output,
    node positions and edge control points are (usually) given in inches,
    whereas bounding boxes are (usually) given in points. To quote Plato,
    "that's kinda annoying tbh." I'm like 90% sure Plato said that once.

    NOTE: wait hm should we use something aside from pixels per inch then?
    need to test out.......... yuck

    See http://www.graphviz.org/doc/info/attrs.html#d:bb and
    http://www.graphviz.org/doc/info/attrs.html#k:rect for reference.
    """
    x1, y1, x2, y2 = bb_string.split(",")
    if x1 != "0" or y1 != "0":
        raise ValueError(
            "Bounding box doesn't start at (0, 0): {}".format(bb_string)
        )
    x2i = float(x2) / layout_config.PIXELS_PER_INCH
    y2i = float(y2) / layout_config.PIXELS_PER_INCH
    return x2i, y2i


def infer_bb(x, y, w, h):
    """Infers the bounding box of a rectangle based on its center point."""
    half_w = (w * layout_config.PIXELS_PER_INCH) / 2
    half_h = (h * layout_config.PIXELS_PER_INCH) / 2
    left = x - half_w
    right = x + half_w
    bottom = y - half_h
    top = y + half_h
    return {"l": left, "r": right, "b": bottom, "t": top}


def get_node_dot(
    nid, lbl, w, h, shape, indent=layout_config.INDENT, color=None
):
    cs = ""
    if color is not None:
        cs = f',fillcolor="{color}"'
    return (
        f"{indent}{nid} "
        f"[width={w},"
        f"height={h},"
        f"shape={shape},"
        f'label="{lbl}"'
        f"{cs}];\n"
    )


def get_edge_dot(srcid, tgtid, is_fake=False, indent=layout_config.INDENT):
    attrs = ""
    if is_fake:
        attrs = f" [{layout_config.FAKEEDGE_STYLE}]"
    return f"{indent}{srcid} -> {tgtid}{attrs};\n"


def get_pattern_cluster_dot(pattern, indent=layout_config.INDENT):
    """Creates a DOT string describing this pattern and its descendants.

    This does, like, use recursion to do this, but it's not really "recursive
    layout" -- we're not laying out each individual pattern. We're just
    getting the entire string and then we'll lay that out separately.

    References
    ----------
    This used to be Pattern.to_dot(): https://github.com/marbl/MetagenomeScope/blob/3667504555508d32ea63ad867e91153dea197045/metagenomescope/graph/pattern.py#L218-L245
    Shoutouts to me from like three years ago lol
    """
    # inner indentation level
    ii = indent + layout_config.INDENT
    dot = f"{indent}subgraph cluster_{pattern.name} {{\n"
    dot += f'{ii}style="filled";\n'
    dot += f'{ii}color="{config.PT2COLOR[pattern.pattern_type]}";\n'
    for node in pattern.nodes:
        if node.compound:
            dot += get_pattern_cluster_dot(node, indent=ii)
        else:
            dot += node.to_dot(indent=ii)
    for edge in pattern.edges:
        dot += edge.to_dot(level="new", indent=ii)
    dot += f"{indent}}}\n"
    return dot
