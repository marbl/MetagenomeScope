from metagenomescope.errors import GraphParsingError


def check_enough_line_parts(line, parts, minpartct):
    if len(parts) < minpartct:
        raise GraphParsingError(f"< {minpartct:,} parts: GFA line '{line}'")


def get_gfa_line_parts(line, minpartct):
    # In python, calling .split() without any parameters means that it
    # will "split on any whitespace character". We don't want to do this,
    # because O-lines in GFA 2 files use space to separate the contents
    # of the path within a single tab-separated column. You can't forget the
    # O-lines dude. Forgetting about the O-lines is like basically the worst
    # thing you can ever do. Imagine like a future where we get rid of A-line
    # dresses and replace them with O-line dresses and it's just a big donut
    # costume. thatd be great. hey is anybody even reading this
    parts = line.strip().split("\t")
    check_enough_line_parts(line, parts, minpartct)
    return parts


def get_tag_dict(tags):
    """Converts a list of tags to a dict mapping tag name and type -> value.

    Parameters
    ----------
    tags: list of str
        Something like ["LN:i:12345", "KC:i:333", ...]

    Returns
    -------
    dict of str -> str
        Maps lowercased tag prefixes (e.g. "ln:i") to tag values (e.g.
        "12345").

        Yeah yeah yeah the GFA specifications officially say that tags with
        lowercase letters are "reserved for end users" but like there are
        real tools out there which can generate lowercase tags (e.g. Flye's
        "dp:i" tags) so let's just convert everything to lowercase and move
        on with our lives to more important questions than file format parsing

    Raises
    ------
    GraphParsingError
        - If we see a tag that doesn't have at least two ":"s

        - If we see a tag where the prefix or value has a length of zero
          (in practice, this can only possibly trigger at the moment when
          the value has a length of zero -- e.g. "LN:i:").

        - If we see the same tag multiple times. Note that this check is
          performed AFTER converting all tag prefixes to lowercase, so if a
          line has both "DP:i:" and "dp:i:" then that will trigger this error.
          Life is too short to mess around with these ambiguities
    """
    lowerpref2val = {}
    for t in tags:
        # figure out the location of the second colon in t
        # (e.g. for something like "LN:i:123:456:789" this is 4)
        #                               ^
        #                           0123456789012345
        #                           0000000000111111
        #
        # I think in GFA 2 tag names can technically be longer than two
        # characters so SURE let's go crazy and make this flexible i guess
        # not that it matters much atm
        colon_ct = 0
        # in theory you could like extract the value of "i" from this loop
        # instead of storing a separate second_colon_idx variable, but i don't
        # trust that to not break in some weird jank corner case
        second_colon_idx = None
        for i, c in enumerate(t):
            if c == ":":
                colon_ct += 1
                if colon_ct == 2:
                    second_colon_idx = i
                    break
        if second_colon_idx is None:
            raise GraphParsingError(f'Found a GFA tag with < 2 colons: "{t}"')
        # do not include the second colon in either the prefix or value
        pref = t[:second_colon_idx]
        val = t[second_colon_idx + 1 :]
        if len(pref) == 0 or len(val) == 0:
            # Since we know there are at least 2 colons in this tag and we are
            # splitting on the second one, we know that len(pref) must be > 0.
            # But, um, I guess we can check it anyway just in case I break
            # something spectacularly later on? sure whatever.
            # (The value can be zero-length though!!! see the tests for that)
            raise GraphParsingError(f'Zero-length tag prefix or value: "{t}"')
        lowerpref = pref.lower()
        if lowerpref in lowerpref2val:
            raise GraphParsingError(f'Duplicate GFA tag prefix: "{lowerpref}"')
        lowerpref2val[lowerpref] = val
    return lowerpref2val


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
