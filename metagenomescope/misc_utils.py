from .errors import WeirdError


def verify_single(objs):
    if len(objs) != 1:
        # We can say "items" here because you say "0 items", "2 items", etc...
        # The only reason to say "item" is if there is "1 item" >:3
        raise WeirdError(f"{objs} contains {len(objs):,} items, instead of 1")


def verify_unique(objs, obj_type="IDs"):
    if len(set(objs)) < len(objs):
        raise WeirdError(f"Duplicate {obj_type}: {objs}")


def pluralize(num, thing="edge"):
    """Pluralizes an integer number of things.

    Parameters
    ----------
    num: int
        Number of things.

    thing: str
        Singular name of the thing.

    Returns
    -------
    str
        If num == 1, then this will be "1 [thing]."
        Otherwise, this will be "[num] [things]."

    Notes
    -----
    Yeah, if you have a thing that has a weird irregular plural (e.g. "beef",
    lol -- https://www.rd.com/list/irregular-plurals/) then this will produce
    something that looks grammatically wonky.

    References
    ----------
    yanked from metaLJA's codebase (... i wrote this)
    """
    if num == 1:
        return f"1 {thing}"
    return f"{num:,} {thing}s"


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


def fmt_qty(quantity, unit="bp", na="N/A"):
    if quantity is not None:
        return f"{quantity:,} {unit}"
    else:
        return na
