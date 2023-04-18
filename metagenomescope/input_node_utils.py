def gc_content(dna_string):
    """Returns the GC content (as a float in the range [0, 1]) of a string of
    DNA, in a 2-tuple with the second element of the tuple being the
    actual number of Gs and Cs in the dna_string.

    Assumes that the string of DNA only contains nucleotides (e.g., it
    doesn't contain any spaces). Passing in an empty string ("") will cause
    this to raise a ValueError.

    For reference, the GC content of a DNA sequence is the percentage of
    nucleotides within the sequence that are either G (guanine) or C
    (cytosine).
    """
    seq_len = len(dna_string)
    if seq_len == 0:
        raise ValueError("Can't compute the GC content of an empty sequence")
    gc_ct = 0
    for nt in dna_string:
        if nt == "G" or nt == "C":
            gc_ct += 1
    return (float(gc_ct) / seq_len), gc_ct


def negate_node_id(id_string):
    """Negates a node ID. Literally, this just adds or removes a starting "-".

    Using this function presumes, of course, that a node's "base" ID in an
    unoriented graph doesn't already start with a "-" character -- because
    that'd mess things up.

    This will raise a ValueError if len(id_string) == 0.
    """
    if len(id_string) == 0:
        raise ValueError("Can't negate an empty node ID")
    if id_string[0] == "-":
        return id_string[1:]
    else:
        return "-" + id_string
