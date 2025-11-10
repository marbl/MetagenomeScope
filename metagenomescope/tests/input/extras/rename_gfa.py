# This isn't fancy well-tested code or anything, but it'll rename the nodes in
# a GFA file and replace sequences with lengths -- in both cases, this can save
# a lot of space and make such a file easier to work with.
#
# This code is pretty brittle -- e.g. it makes the assumption that segments and
# links each only have one extra piece of metadata (coverage for segments,
# CIGAR for links), which will obvs cause problems if this is applied to
# arbitrary GFA files.

with open("sheepgut_g1217.gfa", "r") as f:
    gfa = f.read()

ot = ""
prev = 0
node2idx = {}
for line in gfa.splitlines():
    if not line.startswith("S\t"):

        if line.startswith("L\t"):
            # This an "L" line (link)
            parts = line.split()
            src_idx = node2idx[parts[1]]
            snk_idx = node2idx[parts[3]]
            ot += f"L\t{src_idx}\t{parts[2]}\t{snk_idx}\t{parts[4]}\t{parts[5]}\n"

        else:
            # Another line (... which I assume does not contain node
            # information)
            ot += line + "\n"

    else:
        # This is a "S" line (segment, aka node, even though if this is a de
        # Bruijn graph this'll be an edge. it's a long story)
        parts = line.split()
        seglen = len(parts[2])
        node_idx = prev + 1
        prev += 1
        node2idx[parts[1]] = node_idx
        ot += f"S\t{node_idx}\t*\tLN:i:{seglen}\t{parts[3]}\n"

with open("sheepgut_g1217_nolen.gfa", "w") as of:
    of.write(ot)
