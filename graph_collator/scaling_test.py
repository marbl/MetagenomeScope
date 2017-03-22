#!/usr/bin/env python
#
# Test of different potential scaling methods for AsmViz.
# Things to observe:
# -ensuring that contig length is proportional to total area
# -scaling house "length" (given as "height" here due to rotation stuff) faster
# than house "height" (given as "width" here due to aforementioned reason)
# -trying out "real" (i.e. relative) scaling vs. log scaling
# -how the "roof" of houses scales to large sizes (and ensuring that this is
# consistent in cytoscape.js -- looks like the ratio of ["width" taken up by
# the house roof] to [total node "width"] stays constant regardless of total
# node width).

from math import log, sqrt
import pygraphviz
import numpy

h = pygraphviz.AGraph(rotate="90", packmode="array_c2")
h.node_attr["fixedsize"] = "true"
h.node_attr["shape"] = "invhouse"

# These values can be altered to try out the various scaling methods.
# However, for the sake of relative scaling (scaling method 7) working
# properly, LEN_a should be the minimum size and LEN_g should be the maximum
# size (having multiple min/max values is fine, though).

USING_POWERS_10 = True
if USING_POWERS_10:
    # "scaling_powers10" values
    CONTIG_SET_SUFFIX = "powers10"
    LEN_a = 10
    LEN_b = 100
    LEN_c = 1000
    LEN_d = 10000
    LEN_e = 100000
    LEN_f = 1000000
    LEN_g = 10000000
else:
    # "scaling_close" values
    CONTIG_SET_SUFFIX = "close"
    LEN_a = 500
    LEN_b = 600
    LEN_c = 800
    LEN_d = 1000
    LEN_e = 1500
    LEN_f = 2000
    LEN_g = 3000

def scale_current(bp):
    side_len = log(bp, 10)
    # For nodes with a length of < 10 bp, set a minimum width/height
    if side_len < 1:
        side_len = 1
    return str(side_len)

def scale_2width(bp):
    return str(0.5 * float(scale_current(bp)))

def scale_3width(bp):
    return str(sqrt(float(scale_current(bp))))

def scale_4width(bp):
    return str(0.25 * float(scale_current(bp)))

def scale_7width(bp):
    return str(0.5 * float(scale_7height(bp)))

def scale_7height(bp, max_length=LEN_g, min_length=LEN_a):
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

# Used for both width and height in auto-scaling and Pareto scaling. We
# restrict these two scaling tests to uniform width/height scaling here
# for simplicity -- setting "short side length" = 0.5 * "long side length" or
# something like that would be entirely possible, but this just limits the
# number of different test cases for the time being.
def scale_5(bp):
    if bp < 1:
        return str(1)
    else:
        return str(bp)

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

# Potential scaling: Basically just scaling method 2 (logarithmic scaling,
# "height" grows faster than "width") but with "width" = sqrt("height").
h.add_node("a3", width=scale_3width(LEN_a), height=scale_current(LEN_a))
h.add_node("b3", width=scale_3width(LEN_b), height=scale_current(LEN_b))
h.add_node("c3", width=scale_3width(LEN_c), height=scale_current(LEN_c))
h.add_node("d3", width=scale_3width(LEN_d), height=scale_current(LEN_d))
h.add_node("e3", width=scale_3width(LEN_e), height=scale_current(LEN_e))
h.add_node("f3", width=scale_3width(LEN_f), height=scale_current(LEN_f))
h.add_node("g3", width=scale_3width(LEN_g), height=scale_current(LEN_g))
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

# Potential scaling: divide every contig's length by the standard deviation
# of contig sizes. Referred to as "autoscaling" in van den Berg et al., 2006.
#
# Note that autoscaling, as described in the paper, is preceded by a
# "centering" step in which the mean is subtracted from every value before
# values are divided by the standard deviation -- however, we omit the
# centering step here because it results in negative values being generated,
# and taking the absolute value of those values would result in some
# incorrectly scaled nodes. (Also, it could theoretically result in values of
# 0, which wouldn't make any sense for the side length of a drawing.)
s = numpy.std([LEN_a, LEN_b, LEN_c, LEN_d, LEN_e, LEN_f, LEN_g])
#m = numpy.mean([LEN_a, LEN_b, LEN_c, LEN_d, LEN_e, LEN_f, LEN_g])
h.add_node("a5", width=scale_5((LEN_a)/s), height=scale_5((LEN_a)/s))
h.add_node("b5", width=scale_5((LEN_b)/s), height=scale_5((LEN_b)/s))
h.add_node("c5", width=scale_5((LEN_c)/s), height=scale_5((LEN_c)/s))
h.add_node("d5", width=scale_5((LEN_d)/s), height=scale_5((LEN_d)/s))
h.add_node("e5", width=scale_5((LEN_e)/s), height=scale_5((LEN_e)/s))
h.add_node("f5", width=scale_5((LEN_f)/s), height=scale_5((LEN_f)/s))
h.add_node("g5", width=scale_5((LEN_g)/s), height=scale_5((LEN_g)/s))
h.add_subgraph(["a5", "b5", "c5", "d5", "e5", "f5", "g5"], name="cluster_5")

# Potential scaling: like "autoscaling", but divide every contig's length
# by the square root of the standard deviation of contig sizes.
# Referred to as "Pareto scaling" in van den Berg et al., 2006.
# Note that, as with autoscaling, we omit the centering step used in the paper
# before division by the square root of the standard deviation.
# Also, since the square root of the standard deviation is not large enough to
# reduce the value of some of the outlying values (e.g. the LEN_g contig) to a
# sane (for drawing) amount, we logarithmically scale these values. So ... I
# don't really know if this worth being called "Pareto scaling," since I had to
# make these compromises.
q = sqrt(s)
h.add_node("a6", width=scale_current(LEN_a/q), height=scale_current(LEN_a/q))
h.add_node("b6", width=scale_current(LEN_b/q), height=scale_current(LEN_b/q))
h.add_node("c6", width=scale_current(LEN_c/q), height=scale_current(LEN_c/q))
h.add_node("d6", width=scale_current(LEN_d/q), height=scale_current(LEN_d/q))
h.add_node("e6", width=scale_current(LEN_e/q), height=scale_current(LEN_e/q))
h.add_node("f6", width=scale_current(LEN_f/q), height=scale_current(LEN_f/q))
h.add_node("g6", width=scale_current(LEN_g/q), height=scale_current(LEN_g/q))
h.add_subgraph(["a6", "b6", "c6", "d6", "e6", "f6", "g6"], name="cluster_6")

# Potential scaling: scale "height" relative to min/max contig sizes (max
# contig length gets a width of 7 inches, min gets a width of 1 inch --
# intermediate values are scaled accordingly). width = 0.5 * height.
h.add_node("a7", width=scale_7width(LEN_a), height=scale_7height(LEN_a))
h.add_node("b7", width=scale_7width(LEN_b), height=scale_7height(LEN_b))
h.add_node("c7", width=scale_7width(LEN_c), height=scale_7height(LEN_c))
h.add_node("d7", width=scale_7width(LEN_d), height=scale_7height(LEN_d))
h.add_node("e7", width=scale_7width(LEN_e), height=scale_7height(LEN_e))
h.add_node("f7", width=scale_7width(LEN_f), height=scale_7height(LEN_f))
h.add_node("g7", width=scale_7width(LEN_g), height=scale_7height(LEN_g))
h.add_subgraph(["a7", "b7", "c7", "d7", "e7", "f7", "g7"], name="cluster_7")

h.layout(prog='dot')
h.draw("scaling_" + CONTIG_SET_SUFFIX + ".png")
#h.draw("scaling_test.xdot")
h.clear()
h.close()
