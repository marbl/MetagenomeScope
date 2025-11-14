import random
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
