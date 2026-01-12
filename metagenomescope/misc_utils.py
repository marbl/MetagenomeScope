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


def get_basename_if_fp(fp):
    if fp is None:
        return None
    else:
        return os.path.basename(fp)


def move_to_start_if_in(things, t):
    if t in things:
        things.remove(t)
        things.insert(0, t)


def verify_exactly_one_nonempty(*collections):
    nonempty_seen = False
    for c in collections:
        if len(c) > 0:
            if nonempty_seen:
                raise WeirdError("Multiple collections nonempty")
            nonempty_seen = True
    if not nonempty_seen:
        raise WeirdError("All collections are empty")
