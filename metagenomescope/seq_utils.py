from .errors import WeirdError


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
        raise WeirdError("Can't compute the GC content of an empty sequence")
    gc_ct = 0
    for nt in dna_string:
        if nt == "G" or nt == "C":
            gc_ct += 1
    return (float(gc_ct) / seq_len), gc_ct


def n50(seq_lengths):
    """Determines the N50 statistic of an assembly, given its seq lengths.

    Note that multiple definitions of the N50 statistic exist (see
    https://en.wikipedia.org/wiki/N50,_L50,_and_related_statistics for
    more information).

    Here, we use the calculation method described by Yandell and Ence,
    2012 (Nature) -- see
    http://www.nature.com/nrg/journal/v13/n5/box/nrg3174_BX1.html for a
    high-level overview.
    """
    if len(seq_lengths) == 0:
        raise WeirdError("Can't compute the N50 of an empty list")
    sorted_lengths = sorted(seq_lengths, reverse=True)
    i = 0
    running_sum = 0
    half_total_length = 0.5 * sum(sorted_lengths)
    while running_sum < half_total_length:
        if i >= len(sorted_lengths):
            # This should never happen, but just in case
            raise WeirdError("Bizarre N50 error; should never happen")
        running_sum += sorted_lengths[i]
        i += 1
    # Return length of shortest seq that was used in the running sum
    return sorted_lengths[i - 1]
