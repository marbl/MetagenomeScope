import os
from .errors import WeirdError


def verify_single(objs):
    if len(objs) != 1:
        # We can say "items" here because you say "0 items", "2 items", etc...
        # The only reason to say "item" is if there is "1 item" >:3
        raise WeirdError(f"{objs} contains {len(objs):,} items, instead of 1")


def verify_unique(objs, obj_type="IDs"):
    if len(set(objs)) < len(objs):
        raise WeirdError(f"Duplicate {obj_type}: {objs}")


def verify_subset(s1, s2, custom_message=None):
    """Verifies that s1 is a subset of s2.

    Note that, if s1 and s2 are identical, then they are still subsets of each
    other. That's fine.

    Parameters
    ----------
    s1: collection

    s2: collection

    custom_message: str or None
        If this is None, we'll display a simple error message if s1 is not a
        subset of s2 (listing out both collections). This can be cumbersome if
        s1 and/or s2 are really large, so -- if custom_message is not None --
        we'll display that string as our error message instead.
    """
    if not set(s1).issubset(set(s2)):
        if custom_message is None:
            msg = f"{s1} is not a subset of {s2}"
        else:
            msg = custom_message
        raise WeirdError(msg)


def safe_list_discard(t, e):
    """Tries to remove a single occurrence of element e from list t.

    If e is not in t, then this will not raise an error. Otherwise,
    one occurrence of e in t will be removed (which occurrence it is
    is controlled by list.remove(); as of writing, it should be the first
    occurrence).

    Parameters
    ----------
    t: list

    e: element

    Returns
    -------
    None
        (This modifies t in-place.)

    Notes
    -----
    Tragically, there really isn't an elegant and efficient way to do this
    using just the Python standard library (at least according to
    https://old.reddit.com/r/Python/comments/1spcsq). Hence this being its
    own function lol
    """
    try:
        t.remove(e)
    except ValueError:
        pass


def get_basename_if_fp(fp):
    if fp is None:
        return None
    else:
        return os.path.basename(fp)


def move_to_start_if_in(things, t):
    if t in things:
        things.remove(t)
        things.insert(0, t)


def move_to_end_if_in(things, t):
    if t in things:
        things.remove(t)
        things.append(t)


def expand2tuples(t):
    """Expands 2-tuples within a list.

    Parameters
    ----------
    t: list

    Returns
    -------
    list
        We go through t from left to right. When we see a 2-tuple (x, y) at
        position i, we delete it and replace it with the following element(s):

            1. If there not a previous entry in the list, or if this previous
               entry exists and is not x, then ADD x.

            2. If there is not a next entry in the list, or if this next entry
               in the list exists and is not y, then ADD y.

        Note that this handles multiple 2-tuples occurring one after another:
        something like [(a, b), (b, c), (c, d)] will be expanded to
        [a, b, c, d].
    """
    i = 0
    while i < len(t):
        ele = t[i]
        if type(ele) is tuple:
            srcid, tgtid = ele
            del t[i]
            # Unless the thing directly to the left of position
            # i is srcid, add srcid at position i.
            if i == 0 or t[i - 1] != srcid:
                t.insert(i, srcid)
                i += 1
            # Unless the thing directly to the right of
            # position i is tgtid, add tgtid at position i + 1.
            if i == len(t) or t[i] != tgtid:
                t.insert(i, tgtid)
            i += 1
        else:
            i += 1
    return t
