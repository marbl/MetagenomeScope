from . import config
from .errors import WeirdError, GraphParsingError


def negate(n):
    """Negates a (node) name. Literally just adds or removes a starting "-".

    Um, that is, "config.REV".

    Using this function assumes, of course, that a node's "base" name in an
    unoriented aka "implicit" graph (GFA / LastGraph files, as of writing)
    doesn't already start with a config.REV character -- because that'd mess
    things up. The GFA / LastGraph parsers should check for this and reject
    such graphs.
    """
    if type(n) is not str:
        raise WeirdError(
            "We should've already converted node names to strings. This "
            "should never happen."
        )

    if len(n) == 0:
        raise WeirdError("We should've already screened for empty node names?")

    if n[0] == config.REV:
        return n[1:]
    else:
        return config.REV + n


def has_leftsplit_suffix(name):
    return name.endswith(config.SPLIT_LEFT_SUFFIX)


def has_rightsplit_suffix(name):
    return name.endswith(config.SPLIT_RIGHT_SUFFIX)


def has_split_suffix(name):
    return has_leftsplit_suffix(name) or has_rightsplit_suffix(name)


def get_splitname_base(name):
    if has_split_suffix(name):
        return name[:-2]
    raise WeirdError(f"Node name {name} does not have a split suffix?")


def _sanity_check_name(name, node=True):
    if node:
        aobj = "A node"
        objs = "Nodes"
        named = "named"
        lbl = "name"
    else:
        # ABSURDLY obsessive nobody is going to ever even see this error msg
        # the dsm-6 is going to be just screenshots of this code
        aobj = "An edge"
        objs = "Edges"
        named = "with the ID"
        lbl = "ID"

    if len(name) == 0:
        raise GraphParsingError(
            f"{aobj} with an empty {lbl} exists in the graph?"
        )

    errprefix = f'{aobj} {named} "{name}" exists in the graph.'

    if name.strip() != name:
        raise GraphParsingError(
            f"{errprefix} {objs} cannot have {lbl}s that start or end with "
            "whitespace."
        )

    if node:
        # Node names shouldn't end in -L or -R
        # https://github.com/marbl/MetagenomeScope/issues/272
        if has_split_suffix(name):
            raise GraphParsingError(
                f"{errprefix} {objs} cannot have {lbl}s that end in "
                f'"{config.SPLIT_LEFT_SUFFIX}" or '
                f'"{config.SPLIT_RIGHT_SUFFIX}".'
            )

    if "," in name:
        raise GraphParsingError(
            f"{errprefix} {objs} cannot have {lbl}s that contain commas."
        )


def sanity_check_node_name(name):
    """Ensures that a node name seems reasonable."""
    return _sanity_check_name(name, node=True)


def sanity_check_edge_id(eid):
    """Ensures that an edge ID seems reasonable."""
    return _sanity_check_name(eid, node=False)


def condense_splits(node_names):
    """Condenses a list of node names to merge splits of the same node name.

    Parameters
    ----------
    node_names: list of str

    Returns
    -------
    condensed_names: list of str

    Notes
    -----
    This ignores names that do not have split suffixes. This means that you
    shouldn't include split nodes' basenames in the input: for example, if you
    include both "40-L" and "40" in the list, then this function won't detect
    that this should be condensed (so the output will include both names).
    And if you include "40-L", "40-R", and "40" in the list, then this will
    result in two "40"s in your output (which you probably don't want).
    """
    # We can already assume uniqueness here, but let's be careful
    sorted_names = sorted(set(node_names))
    i = 0
    condensed_names = []
    while i < len(sorted_names) - 1:
        n = sorted_names[i]
        # we know that "40-L" should occur before "40-R" in sorted_names
        if has_leftsplit_suffix(n):
            base = get_splitname_base(n)
            if sorted_names[i + 1] == base + config.SPLIT_RIGHT_SUFFIX:
                condensed_names.append(base)
                i += 2
                continue
        condensed_names.append(n)
        i += 1
    if i == len(sorted_names) - 1:
        condensed_names.append(sorted_names[i])
    return condensed_names
