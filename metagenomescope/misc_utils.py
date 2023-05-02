from .errors import WeirdError


def verify_single(objs):
    if len(objs) != 1:
        raise WeirdError(f"{objs} contains {len(objs):,} items, instead of 1")


def verify_unique(objs, obj_type="IDs"):
    if len(set(objs)) < len(objs):
        raise WeirdError(f"Duplicate {obj_type}: {objs}")


def verify_subset(s1, s2):
    """Verifies that s1 is a subset of s2.

    Note that, if s1 and s2 are identical, then they are still subsets of each
    other. That's fine.
    """
    if not set(s1).issubset(set(s2)):
        raise WeirdError(f"{s1} is not a subset of {s2}")
