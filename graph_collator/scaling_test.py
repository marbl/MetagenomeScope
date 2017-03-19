#!/usr/bin/env python
# Test of different potential scaling methods for AsmViz.
# Things to observe:
# -relationship btwn. contig length and total area
# -how the "roof" of houses scales to large sizes (and ensuring that this is
# constant in cytoscape.js)

from math import log
import pygraphviz

h = pygraphviz.AGraph(rotate="90")
h.node_attr["fixedsize"] = "true"
h.node_attr["shape"] = "invhouse"

LEN_a = 10
LEN_b = 100
LEN_c = 1000
LEN_d = 10000
LEN_e = 100000
LEN_f = 1000000
LEN_g = 10000000

def scale_current(bp):
    side_len = log(bp, 10)
    # For nodes with a length of < 10 bp, set a minimum width/height
    if side_len < 1:
        side_len = 1
    return str(side_len)

def scale_2width(bp):
    return str(0.5 * float(scale_current(bp)))

def scale_3height(bp, max_length=LEN_g, min_length=LEN_a):
    if max_length == min_length:
        return str(1)
    diff = float(bp - min_length)
    diff /= (max_length - min_length)
    # Now, diff is a percentage (somewhere from 0 to 1) where 0% = min_length,
    # 100% = max_length, and intermediate values are scaled accordingly.
    # (We use a max height of 7 inches somewhat arbitrarily here.)
    contig_height_range = (7 - 1)
    # Once we've scaled diff by contig_height_range, its possible values are in
    # the inclusive range [0, contig_height_range]. Thus, we add the minimum
    # contig height value to ensure that the lower bound is 1 and the upper
    # bound is the max contig height.
    return str((diff * contig_height_range) + 1)

def scale_3width(bp):
    return str(0.5 * float(scale_3height(bp)))

def scale_4width(bp):
    return str(0.25 * float(scale_current(bp)))

# Current scaling: width = height, and side length = log10(contig length)
h.add_node("a1", width=scale_current(LEN_a), height=scale_current(LEN_a))
h.add_node("b1", width=scale_current(LEN_b), height=scale_current(LEN_b))
h.add_node("c1", width=scale_current(LEN_c), height=scale_current(LEN_c))
h.add_node("d1", width=scale_current(LEN_d), height=scale_current(LEN_d))
h.add_node("e1", width=scale_current(LEN_e), height=scale_current(LEN_e))
h.add_node("f1", width=scale_current(LEN_f), height=scale_current(LEN_f))
h.add_node("g1", width=scale_current(LEN_g), height=scale_current(LEN_g))
h.add_subgraph(["a1", "b1", "c1", "d1", "e1", "f1", "g1"], name="cluster_1")

# Potential scaling: "height" (i.e. side length facing right in
# landscape graph orientation) = log10(contig length), and "width" = half of
# height. This still scales node area sizes, but it grows "height" faster than
# "width," giving the impression of contigs getting "longer."
h.add_node("a2", width=scale_2width(LEN_a), height=scale_current(LEN_a))
h.add_node("b2", width=scale_2width(LEN_b), height=scale_current(LEN_b))
h.add_node("c2", width=scale_2width(LEN_c), height=scale_current(LEN_c))
h.add_node("d2", width=scale_2width(LEN_d), height=scale_current(LEN_d))
h.add_node("e2", width=scale_2width(LEN_e), height=scale_current(LEN_e))
h.add_node("f2", width=scale_2width(LEN_f), height=scale_current(LEN_f))
h.add_node("g2", width=scale_2width(LEN_g), height=scale_current(LEN_g))
h.add_subgraph(["a2", "b2", "c2", "d2", "e2", "f2", "g2"], name="cluster_2")

# Potential scaling: scale "height" relative to min/max contig sizes (max
# contig length gets a width of 7 inches, min gets a width of 1 inch --
# intermediate values are scaled accordingly). width = 0.5 * height.
# Note that this has some problems with outliers, although approaches that circumvent this are possible.
h.add_node("a3", width=scale_3width(LEN_a), height=scale_3height(LEN_a))
h.add_node("b3", width=scale_3width(LEN_b), height=scale_3height(LEN_b))
h.add_node("c3", width=scale_3width(LEN_c), height=scale_3height(LEN_c))
h.add_node("d3", width=scale_3width(LEN_d), height=scale_3height(LEN_d))
h.add_node("e3", width=scale_3width(LEN_e), height=scale_3height(LEN_e))
h.add_node("f3", width=scale_3width(LEN_f), height=scale_3height(LEN_f))
h.add_node("g3", width=scale_3width(LEN_g), height=scale_3height(LEN_g))
h.add_subgraph(["a3", "b3", "c3", "d3", "e3", "f3", "g3"], name="cluster_3")

# Potential scaling: Basically just scaling method 2 (logarithmic scaling,
# "height" grows faster than "width") but with "width" = 0.25*"height" instead
# of a factor of 0.5.
h.add_node("a4", width=scale_4width(LEN_a), height=scale_current(LEN_a))
h.add_node("b4", width=scale_4width(LEN_b), height=scale_current(LEN_b))
h.add_node("c4", width=scale_4width(LEN_c), height=scale_current(LEN_c))
h.add_node("d4", width=scale_4width(LEN_d), height=scale_current(LEN_d))
h.add_node("e4", width=scale_4width(LEN_e), height=scale_current(LEN_e))
h.add_node("f4", width=scale_4width(LEN_f), height=scale_current(LEN_f))
h.add_node("g4", width=scale_4width(LEN_g), height=scale_current(LEN_g))
h.add_subgraph(["a4", "b4", "c4", "d4", "e4", "f4", "g4"], name="cluster_4")

h.layout(prog='dot')
h.draw("scaling_test.png")
# Export h to PNG
h.clear()
h.close()
