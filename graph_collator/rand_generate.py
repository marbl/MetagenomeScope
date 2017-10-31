#!/usr/bin/env python
# Copyright (C) 2017 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
# 
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
####
# Generates a random assembly graph in GML format, with a specified amount of
# structural patterns.
# The current generation algorithm constructs a linear arrangement of the
# number of nodes specified in the -n option. Complexities are thus added to
# the graph.

# TODO: initially, just have this work with bubbles.

import argparse
from random import randrange, random
import networkx as nx

# Get argument information
parser = argparse.ArgumentParser(description="Generates a semi-random " + \
    "assembly graph in GML format.")
parser.add_argument("-o", "--output", required=True,
    help="output file name")
parser.add_argument("-n", "--nodes", required=True,
    help="lower bound on number of nodes in the graph")
parser.add_argument("-b", "--bubbles", required=False, default=-1,
    help="requested number of simple bubbles in the graph")
parser.add_argument("-f", "--ropes", required=False, default=-1,
    help="requested number of frayed ropes in the graph")
parser.add_argument("-c", "--chains", required=False, default=-1,
    help="requested number of chains in the graph")
parser.add_argument("-y", "--cyclic_chains", required=False, default=-1,
    help="requested number of cyclic chains in the graph")

args = parser.parse_args()
node_ct = int(args.nodes)
bubble_ct = int(args.bubbles)
rope_ct = int(args.ropes)
chain_ct = int(args.chains)
cyclic_chain_ct = int(args.cyclic_chains)

G = nx.path_graph(node_ct)
node_orientation_dict = {}
length_dict = {}
for n in G.nodes():
    node_orientation_dict[n] = "FOW" if random() < 0.5 else "REV"
    length_dict[n] = randrange(1, 1000000)

nx.set_node_attributes(G, "orientation", node_orientation_dict)
nx.set_node_attributes(G, "length", length_dict)

orientation_dict = {}
mean_dict = {}
stdev_dict = {}
bsize_dict = {}
for e in G.edges():
    if node_orientation_dict[e[0]] == "FOW":
        if node_orientation_dict[e[1]] == "FOW":
            orientation_dict[e] = "EB"
        else:
            orientation_dict[e] = "EE"
    else:
        if node_orientation_dict[e[1]] == "FOW":
            orientation_dict[e] = "BB"
        else:
            orientation_dict[e] = "BE"
    mean_dict[e] = 0
    stdev_dict[e] = 0
    bsize_dict[e] = 1
nx.set_edge_attributes(G, "orientation", orientation_dict)
nx.set_edge_attributes(G, "mean", mean_dict)
nx.set_edge_attributes(G, "stdev", stdev_dict)
nx.set_edge_attributes(G, "bsize", bsize_dict)
nx.write_gml(G, args.output)
