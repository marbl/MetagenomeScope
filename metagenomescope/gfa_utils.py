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
