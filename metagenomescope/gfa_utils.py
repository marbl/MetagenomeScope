from metagenomescope.errors import GraphParsingError


def check_lengths_consistent(segname, len1, len2):
    if len1 != len2:
        raise GraphParsingError(
            f"Segment '{segname}' has inconsistent lengths: {len1:,}; {len2:,}"
        )


def count2cov_maybe(scountval, slen):
    """Converts a segment's "count" tag value to a coverage, if possible.

    Parameters
    ----------
    scountval: str
        The value from a KC:i, RC:i, or FC:i tag from a S-line in a GFA file.

    slen: int
        The length for this S-line.

    Returns
    -------
    float or None
        If slen > 0, this will be int(scountval) divided by slen -- matching
        Bandage, Gfapy, etc.'s behavior.

        Otherwise, to avoid division by zero, we will just return None --
        so the downstream code can see that this segment does not have a
        defined coverage.

    References
    ----------
    Based on Bandage's behavior:
    https://github.com/rrwick/Bandage/blob/f94d409a76bf6a13eef6af0a88476eaeffa71b32/graph/assemblygraph.cpp#L690-L709
    """
    if slen > 0:
        return int(scountval) / slen
    else:
        return None


def store_gfa_id(i, seenid2type, newtype):
    # GFA 2 allows edges and groups (and gaps, but we don't currently parse
    # those) to have * for an ID, indicating that the ID is not given.
    if i == "*":
        # For edges (E-lines), this is fine -- don't add "*" to the namespace
        if newtype == "E":
            return
        # For paths (O-lines in GFA 2 / P-lines in GFA 1), this is a problem:
        # we want each path to have an identifiable name for the visualization!
        # We COULD just store "*" as a path ID and later throw an error if/when
        # we see another path with ID "*", but that is confusing and lazy. Best
        # to fail early, IMO.
        elif newtype in "OP":
            raise GraphParsingError(
                f'{newtype}-line with placeholder ID "*" found. We do not '
                "support paths without defined IDs."
            )
        # In theory, there's nothing stopping you from naming a segment
        # (S-line) "*" -- the GFA 2 ID regex of [!-~]+ allows it. So I guessss
        # we can just move on with our lives if newtype is not E or O. (If
        # multiple S-lines or whatever have "*" as an ID then we'll eventually
        # trigger the error below about nonunique IDs.)
    if i in seenid2type:
        raise GraphParsingError(f'ID "{i}" not unique.')
    seenid2type[i] = newtype


def check_path_nonempty(path_id, path_children):
    if len(path_children) == 0 or path_children == "*":
        raise GraphParsingError(f"Path {path_id} is empty?")


def is_dovetail(src_orient, tgt_orient, b1, e1, b2, e2):
    """Returns True if a GFA 2 E-line represents a "dovetail" edge.

    Parameters
    ----------
    src_orient: str
    tgt_orient: str
        The orientations of the source and target node. These should be either
        config.FWD or config.REV, but really we are just comparing equality
        here so their exact values don't really matter right now.

    b1: str
    e1: str
    b2: str
    e2: str
        The position intervals given for this GFA 2 edge.

        Basically, these are 0-indexed half-open intervals (like in Python!),
        with the addition that values that indicate one past the last position
        in a sequence must be followed by a $ sign. See the GFA 2 specification
        linked below for details. (Long story short, the $ thing is nice
        because it makes it easy to detect dovetail edges.)

    Returns
    -------
    bool
        True if these intervals represent a dovetail edge, False otherwise.

    Notes
    -----
    - I guess you can think of a dovetail edge as analogous to a typical L-line
      in a GFA 1 file. It is cool that GFA 2 E-lines can represent fancy things
      like containments and other "general" edges (see the GFA 2
      specification's figures), but for basic graph visualization these things
      are not usually what we want to show.

    - We do not currently validate that "$" really indicates the end of the
      sequence. this is partly because there's nothing stopping a GFA file from
      having segments be defined *after* edges, right? Which will make looking
      at S-lines before looking at E-lines more challenging to do. (See the
      all_line_types test inputs for examples of that...)

      Also there is weird jank where in GFA 2 the length given for a segment
      is allowed to differ from its actual length. I am not 100% sure what this
      means for edge intervals that refer to such segments -- my GUESS is that
      they refer to the actual segment sequence (with a different length), but
      it is unclear.

      Anyway, all of this is to say that for now we just assume that whoever
      created this graph correctly created the "$" signs. Eventually it would
      be nice to do more validation (e.g. detecting missing "$"s, or situations
      where a "$" was defined incorrectly), but I am not sure GFA 2 is not
      really widely-used enough for this to be something worth worrying about.

    References
    ----------
    https://gfa-spec.github.io/GFA-spec/GFA2.html#edge
    """
    orientations_match = src_orient == tgt_orient
    # The GFA 2 specification writes out these exact rules, so thanks to them
    # for making this refreshingly simple to detect
    if orientations_match:
        return (b1 == "0" and e2[-1] == "$") or (b2 == "0" and e1[-1] == "$")
    else:
        return (b1 == "0" and b2 == "0") or (e1[-1] == "$" and e2[-1] == "$")
