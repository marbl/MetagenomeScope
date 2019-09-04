#!/usr/bin/env python3
# Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
#
# Requires NetworkX. Only "1.X" versions of NetworkX are supported; version 2
# seems to break some functionality here.

import argparse
from random import randrange, random, choice
import networkx as nx

# Get argument information
parser = argparse.ArgumentParser(
    description="Generates a semi-random " + "assembly graph in GML format."
)
parser.add_argument("-o", "--output", required=True, help="output file prefix")
parser.add_argument(
    "-n",
    "--nodes",
    required=True,
    help="lower bound on number of nodes in the graph",
)
parser.add_argument(
    "-b",
    "--bubbles",
    required=False,
    default=0,
    help="requested number of simple bubbles in the graph",
)
# parser.add_argument("-f", "--ropes", required=False, default=-1,
#    help="requested number of frayed ropes in the graph")
# parser.add_argument("-c", "--chains", required=False, default=-1,
#    help="requested number of chains in the graph")
# parser.add_argument("-y", "--cyclic_chains", required=False, default=-1,
#    help="requested number of cyclic chains in the graph")

args = parser.parse_args()
node_ct = int(args.nodes)
bubble_ct = int(args.bubbles)
# rope_ct = int(args.ropes)
# chain_ct = int(args.chains)
# cyclic_chain_ct = int(args.cyclic_chains)

# Validate arguments a bit
if node_ct <= 0:
    raise ValueError("graph must have a lower bound of 1 node")
if bubble_ct < 0:
    raise ValueError("bubble count must be a nonnegative integer")

G = nx.path_graph(node_ct, nx.DiGraph())
bubble_id = 0


def assign_rand_attrs(G):
    """Assigns random attributes to the nodes/edges in a specified nx graph.

       This should only be called after all nodes and edges have been
       added to the graph.
    """
    node_orientation_dict = {}
    length_dict = {}
    for n in G.nodes():
        node_orientation_dict[n] = "FOW" if random() < 0.5 else "REV"
        length_dict[n] = randrange(1, 1000000)

    nx.set_node_attributes(G, name="orientation", values=node_orientation_dict)
    nx.set_node_attributes(G, name="length", values=length_dict)

    # Assign edge attrs
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
    nx.set_edge_attributes(G, name="orientation", values=orientation_dict)
    nx.set_edge_attributes(G, name="mean", values=mean_dict)
    nx.set_edge_attributes(G, name="stdev", values=stdev_dict)
    nx.set_edge_attributes(G, name="bsize", values=bsize_dict)


def create_bubble():
    """Creates a bubble with a random number of nodes between 4 and 17.
       These bubbles are "simple" in that they always consist of a source,
       sink, and 2 or 3 branching middle paths which can contain anywhere from
       1 to 5 nodes each.

       Returns the interior paths in the bubble.
    """
    global bubble_id

    if random() < 0.5:
        num_middle_paths = 2
    else:
        num_middle_paths = 3

    # paths is a list of subgraphs indicating the paths in the bubble
    paths = []
    path_id = 0
    for p in range(num_middle_paths):
        num_nodes_on_path = randrange(1, 6)
        prefix = "b%dp%d_" % (bubble_id, path_id)
        P = nx.path_graph(num_nodes_on_path, nx.DiGraph())
        P.graph["bpid"] = prefix
        P.graph["terminus"] = prefix + str(num_nodes_on_path - 1)
        mapping = {}
        for n in P.nodes():
            mapping[n] = prefix + "%d" % (n)
        P = nx.relabel_nodes(P, mapping)
        paths.append(P)
        path_id += 1
    bubble_id += 1
    return paths


for i in range(bubble_ct):
    paths = create_bubble()
    src = choice(G.nodes())
    # Since we start with a linear structure (a "path graph"), if we decide to
    # create a bubble starting at the last node in this structure then we have
    # to add an additional node to serve as the sink of the bubble starting at
    # what was formerly the last node. This process could conceivably be
    # repeated an arbitrary number of times if the current last node is
    # repeatedly selected as the source of a new bubble.
    if G.out_edges(src) == []:
        new_sink_id = str(src) + "_snk"
        G.add_node(new_sink_id)
        G.add_edge(src, new_sink_id)
        print("had to make a new sink")
    snk = choice(G.out_edges(src))[1]
    for P in paths:
        G.add_nodes_from(P)
        G.add_edges_from(P.edges())
        G.add_edge(src, P.graph["bpid"] + "0")
        G.add_edge(P.graph["terminus"], snk)
    print("created bubble between", src, "and", snk)
    G.remove_edge(src, snk)

assign_rand_attrs(G)
nx.write_gml(G, args.output + ".gml")
