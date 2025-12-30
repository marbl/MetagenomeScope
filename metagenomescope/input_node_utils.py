from . import config
from .errors import WeirdError, GraphParsingError


def negate_node_id(id_string):
    """Negates a node ID. Literally, this just adds or removes a starting "-".

    Using this function presumes, of course, that a node's "base" ID in an
    unoriented graph doesn't already start with a "-" character -- because
    that'd mess things up.

    This will raise a ValueError if len(id_string) == 0.
    """
    if type(id_string) is not str:
        raise WeirdError(
            "We should've already converted node names to strings. This "
            "should never happen."
        )

    if len(id_string) == 0:
        raise WeirdError("We should've already screened for empty node names?")

    if id_string[0] == "-":
        return id_string[1:]
    else:
        return "-" + id_string


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
