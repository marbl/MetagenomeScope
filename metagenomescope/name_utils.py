from . import config
from .errors import WeirdError, GraphParsingError


def negate(n):
    """Negates a (node) name. Literally just adds or removes a starting "-".

    Using this function assumes, of course, that a node's "base" name in an
    unoriented aka "implicit" graph (GFA / LastGraph files, as of writing)
    doesn't already start with a "-" character -- because that'd mess things
    up. The GFA / LastGraph parsers should check for this and reject such
    graphs.
    """
    if type(n) is not str:
        raise WeirdError(
            "We should've already converted node names to strings. This "
            "should never happen."
        )

    if len(n) == 0:
        raise WeirdError("We should've already screened for empty node names?")

    if n[0] == "-":
        return n[1:]
    else:
        return "-" + n


def sanity_check_node_name(name):
    """Ensures that a node name seems reasonable."""

    if len(name) == 0:
        raise GraphParsingError(
            "A node with an empty name exists in the graph?"
        )

    if name.strip() != name:
        raise GraphParsingError(
            f'A node named "{name}" exists in the graph. Nodes cannot have '
            "names that start or end with whitespace."
        )

    # Node names shouldn't end in -L or -R
    # https://github.com/marbl/MetagenomeScope/issues/272
    left_suff = config.SPLIT_SEP + config.SPLIT_LEFT
    right_suff = config.SPLIT_SEP + config.SPLIT_RIGHT
    if name.endswith(left_suff) or name.endswith(right_suff):
        raise GraphParsingError(
            f'A node named "{name}" exists in the graph. Nodes cannot have '
            f'names that end in "{left_suff}" or "{right_suff}".'
        )
