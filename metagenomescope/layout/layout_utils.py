import math
from . import layout_config
from .. import config
from ..errors import WeirdError


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
    coords = [float(c) for c in points_str.split()]
    if len(coords) % 2 != 0:
        raise ValueError("Invalid GraphViz edge control points: {pos}")
    return coords


def shift_control_points(coords, left, bottom):
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
    new_coords = []
    for i, coord in enumerate(coords):
        if i % 2 == 0:
            # This is an x position (since the list is [x, y, x, y, ...])
            new_coords.append(left + coord)
        else:
            # This is a y position
            new_coords.append(bottom + coord)

    # We should have ended on a y position. If we didn't, something is
    # seriously wrong.
    if i % 2 == 0:
        raise ValueError(f"Non-even number of control points: {coords}")
    return new_coords


def euclidean_distance(p1, p2):
    # https://en.wikipedia.org/wiki/Euclidean_distance
    # just sqrt(dx^2 + dy^2)
    return math.sqrt(((p2[0] - p1[0]) ** 2) + ((p2[1] - p1[1]) ** 2))


def point_to_line_distance(point, a, b):
    """Returns perpendicular distance from a point to a line (from a to b).

    Parameters
    ----------
    point: (float, float)

    a: (float, float)

    b: (float, float)

    Returns
    -------
    dist: float

    Notes
    -----
    Given a line that passes through two points (a and b), this function
    returns the perpendicular distance from a point to the line.

    Note that, unlike most formulations of point-to-line-distance, the value
    returned here isn't necessarily nonnegative. This is because Cytoscape.js
    expects the control-point-distances used for unbundled-bezier edges to have
    a sign based on which "side" of the line from source node to sink node
    they're on:

          negative
    SOURCE ------> TARGET
          positive

    So here, if this edge has a bend "upwards," we'd give the corresponding
    control point a negative distance from the line, and if the bend was
    "downwards" it'd have a positive distance from the line. You can see this
    for yourself here (http://js.cytoscape.org/demos/edge-types/) -- notice how
    the control-point-distances for the unbundled-bezier (multiple) edge are
    [40, -40] (a downward bend, then an upwards bend).

    What that means here is that we don't take the absolute value of the
    numerator in this formula; instead, we negate it. This makes these distances
    match up with what Cytoscape.js expects. (I'll be honest: I don't know why
    this works. This is just what I found back in 2016. As a big heaping TODO,
    I should really make this more consistent, or at least figure out *why* this
    works -- it's worth noting that if you swap around linePoint1 and
    linePoint2, this'll negate the distance you get, and I have no idea why this
    is working right now.)

    Raises
    ------
    WeirdError
        If distance(a, b) is equal to 0 (since this would make the
        point-to-line-distance formula undefined, due to having 0 in the
        denominator). So don't define a line by the same point twice!!!

    References
    ----------
    The formula used here is based on
    https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points.
    """
    line_distance = euclidean_distance(a, b)
    if line_distance == 0:
        raise WeirdError("Line distance is zero?")
    ydelta = b[1] - a[1]
    xdelta = b[0] - a[0]
    x2y1 = b[0] * a[1]
    y2x1 = b[1] * a[0]
    x0, y0 = point
    numerator = (ydelta * x0) - (xdelta * y0) + x2y1 - y2x1
    return -numerator / line_distance


def dot_to_cyjs_control_points(
    src_pos, tgt_pos, coords, flipheight, left=None, bottom=None
):
    """Shifts edge control points and converts them to Cytoscape.js format.

    Parameters
    ----------
    src_pos: (float, float)

    tgt_pos: (float, float)

    coords: list of float

    flipheight: float

    left: float or None

    bottom: float or None

    Returns
    -------
    just_a_straight_line, dists, weights: bool, str, str
        If just_a_straight_line is True, you can easily approximate this
        with just a straight line.

        dists and weights can be used as the control-point-distances and
        control-point-weights properties in Cytoscape.js, respectively.

    Notes
    -----
    Adapted from my old JS code:
    https://github.com/marbl/MetagenomeScope/blob/0db5e3790fc736f428f65b4687bd4d1e054c3978/viewer/js/xdot2cy.js#L5129-L5185
    """
    if left is not None and bottom is not None:
        coords = shift_control_points(coords, left, bottom)
    for i in range(len(coords)):
        if i % 2 == 1:
            coords[i] = flipheight - coords[i]
    src_tgt_dist = euclidean_distance(src_pos, tgt_pos)
    cpdists = ""
    cpweights = ""
    just_a_straight_line = True
    i = 0
    while i < len(coords):
        curr_pt = (coords[i], coords[i + 1])
        pld = point_to_line_distance(curr_pt, src_pos, tgt_pos)
        pldsq = pld**2
        dsp = euclidean_distance(curr_pt, src_pos)
        dtp = euclidean_distance(curr_pt, tgt_pos)

        # The interiors of the sqrts below should always be positive, but
        # rounding jank can cause them to become slightly negative (or at
        # least that was a thing I had to account for in JS). Hence the abs().
        ws = math.sqrt(abs(dsp**2 - pldsq))
        wt = math.sqrt(abs(dtp**2 - pldsq))

        # Get the weight of the control point on the line between source and
        # sink oriented properly; if the control point is "behind" the source
        # node we make it negative, and if it is "past" the sink node we make
        # it > 1. Everything in between the source and sink falls within [0, 1]
        # inclusive.
        if wt > src_tgt_dist and wt > ws:
            # ctrl point is "behind" the source node
            w = -ws / src_tgt_dist
        else:
            # ctrl point is anywhere past the source node
            w = ws / src_tgt_dist

        # Is this control point far enough away from the straight line between
        # the source and target node?
        if abs(pld) > layout_config.CTRL_PT_DIST_EPSILON:
            just_a_straight_line = False

        # control points with a weight of 0 (first ctrl pt) or 1 (last ctrl pt)
        # aren't valid due to implicit points already "existing there." see
        # github.com/cytoscape/cytoscape.js/issues/1451. This preemptively
        # fixes such control points.
        # TODO: or maybe we should just skip these lmao ...?
        if i == 0 and w == 0:
            w = 0.01
        elif i == len(coords) - 2 and w == 1:
            w = 0.99

        space = ""
        if i > 0:
            space = " "
        cpdists += f"{space}{pld:.4f} "
        cpweights += f"{space}{w:.4f} "
        i += 2
    return just_a_straight_line, cpdists, cpweights


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
