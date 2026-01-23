import random
from . import cy_config
from .errors import WeirdError


def get_rand_idx_list(n):
    """Given an int n > 0, returns a random list of all ints in [0, n)."""
    if n < 1:
        raise WeirdError("n must be > 0")
    available_indices = list(range(n))
    random.shuffle(available_indices)
    return available_indices


def get_rand_idx(n):
    """Generates random indices in [0, n) while trying to avoid nearby repeats.

    Parameters
    ----------
    n: int
        A positive integer describing the number of possible indices.
        For example, if n = 5, then we will generate indices from the range
        [0, 1, 2, 3, 4].

    Yields
    ------
    int
        A random integer from the range [0, n).

    Notes
    -----

    Motivation
    ~~~~~~~~~~
    For tiny graphs, there is the risk that we select the same color a bunch of
    times. This can look a bit gross, and it is super obvious when many nodes
    and edges in the graph are drawn at once.

    One way to accommodate this is to force the selection of random
    indices to be "cyclic": once we assign an index, we should then
    not assign it again until we've assigned all other possible indices.
    We could easily do this by just, like, maintaining a counter
    variable and then computing that modulo the number of possible indices
    to figure out what index to assign an arbitrary node/edge.

    This approach works but it is too "consistent," in my opinion --
    something about starting with red every time seems boring. Also
    it's not even random??? So, this generator implements this approach, BUT
    we shuffle the order of the indices in advance of every "cycle." This way,
    we only see each index once per cycle, but the order of each cycle is
    random.

    Future work
    ~~~~~~~~~~~
    - Arguably this is still a bit too consistent if you set a random seed (which
      is what MetagenomeScope curently does), but that could be addressed by
      exposing the random seed as a CLI parameter.

    - I am aware that you could get unlucky and have something like (for n = 5)
      [1, 2, 3, 0, 4], [4, 2, 3, 1, 0] -- where the last index from one cycle
      is the same as the first index from the next cycle. There are ways to
      account for this but I don't think they are important enough to justify
      pursuing, since the worst-case scenario is that the random colorings just
      look slightly bad.

    References
    ----------
    I was originally going to have this as a nested function within
    AssemblyGraph._init_graph_objs() that used a "nonlocal" counter variable or
    something, but https://stackoverflow.com/a/1261952 made a reasonable case
    for using a generator instead.

    ... in retrospect maybe it would have been better to write this simply but
    whatever now it's easy to test
    """
    available_indices = get_rand_idx_list(n)
    while True:
        if len(available_indices) == 0:
            available_indices = get_rand_idx_list(n)
        yield available_indices.pop()


def selectively_interpolate_hsl(
    positions, light_to_dark=True, Lmin=15, Lmax=70, H=255, S=29
):
    """Linearly interpolates HSL colors along a given lightness range.

    Parameters
    ----------
    positions: list of bool
        Only produce HSL colors for entries of this list marked as True.
        Other entries of this list will get ""s instead.

    light_to_dark: bool
        If True, interpolate from high to low L values (so, earlier
        entries in the output list will be lighter). If False, go from
        low to high.

    Lmin: float
        Minimum lightness.

    Lmax: float
        Maximum lightness.

    H: float
        Hue.

    S: float
        Saturation.

    Returns
    -------
    colors: list of str
        This will have the same dimensions as positions. Each entry in this
        list will be either a HSL color compatible with Plotly or a "",
        depending on the corresponding entry in positions.

    Raises
    ------
    WeirdError
        If Lmax <= Lmin.

    Notes
    -----
    I'm not sure if allowing H, S, and L to all be floats is useful, but
    whatever it doesn't really matter (https://stackoverflow.com/q/5723225).

    Default values picked by messing around in https://www.hslpicker.com.
    This represents a gradient from lightish purple to very dark purple.
    (Um, as of December 30, 2025 I changed the actual application to use
    less saturation, so now it is more like medium gray to black. this helps
    distinguish these rectangles from the other normal ones in the treemap.)

    Note that -- if you are calling this using the treemap rectangles -- then
    the first entry in the "cc_aggs" list, describing all components in the
    graph, will always be False. I guess this will (slightly?) impact the
    lightnesses, but probably not in a very noticeable way.
    """
    if Lmax <= Lmin:
        raise WeirdError("Lmax must be > Lmin")
    d = Lmax - Lmin
    colors = []
    prefix = f"hsl({H},{S}%,"
    for i, a in enumerate(positions):
        if a:
            if light_to_dark:
                # go from high L to low L
                frac = 1 - (i / (len(positions) - 1))
            else:
                frac = i / (len(positions) - 1)
            L = (frac * d) + Lmin
            colors.append(f"{prefix}{L}%)")
        else:
            # blessedly, if you pass "" as a marker_color for a particular
            # treemap entry then plotly understands that we should just follow
            # the usual colormap
            colors.append("")
    return colors


def user_color_to_cyjs(color):
    recognized = False
    if color in cy_config.GVCOLOR2HEX:
        color = cy_config.GVCOLOR2HEX[color]
        recognized = True
    elif (
        color[0] == "#" or color.startswith("rgb(") or color.startswith("hsl(")
    ):
        recognized = True
    # if the color is some random name that we don't recognize don't pass it on
    # to cy.js - just fall back to default uniform edge color
    return recognized, color
