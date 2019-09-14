###############################################################################
# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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
###############################################################################
# This module contains various utility functions for parsing assembly graph
# files. All of the parse_() functions here should return a NetworkX DiGraph
# representing the assembly graph in the input file, assuming the input file is
# "valid."
#
# You can also just call parse(), which will attempt to determine which parser
# should be used for an assembly graph file. (This is what is done in
# MetagenomeScope normally.)
#
# ADDING SUPPORT FOR MORE ASSEMBLY GRAPH FILETYPES
#
# This should be very doable (and hopefully painless). All you'll need to do is
#
#  1. Create a function that takes as input a filename and (if the graph is
#  valid) returns a NetworkX DiGraph representing the contained assembly graph.
#
#  2. Add the lowercase file extension as a key in SUPPORTED_FILETYPE_TO_PARSER
#  that maps to your new function.

import networkx as nx
import gfapy
from .input_node_utils import gc_content, negate_node_id


def attempt_to_validate_lastgraph_file(graph_file):
    """Attempts to verify that this LastGraph file seems "valid."

    Parameters
    ----------
    graph_file: io.TextIOBase
        A "text stream." In normal usage of this function, this should just
        be the output of running open(). However, this can also totally be
        an io.StringIO object or something -- this function is agnostic to
        the type of the file object.

    Discussion
    ----------
    This is by no means a *comprehensive* validation of this file, but it's
    close enough to give us some confidence that we can just parse this
    graph using our simple, fragile-ish line-by-line parser contained in
    parse_lastgraph().

    Raises
    ------
    ValueError
        If any of the following conditions are observed:

        General:
        -The $NUMBER_OF_NODES in the file header does not equal the number
         of NODE declarations in the file

        Any NODE:
        -doesn't have a $NODE_ID, $COV_SHORT1, and $O_COV_SHORT1 value
        -has a $NODE_ID that starts with a "-" character, or has been seen
         before in the file
        -has less than two sequences given*
        -has two sequences given, but the sequences are of unequal lengths (or
         the sequence lengths don't match the node's $COV_SHORT1 value)

        Any ARC:
        -doesn't have a $START_NODE, $END_NODE, and $MULTIPLICITY given
        -refers to a $START_NODE or $END_NODE for which no corresponding
         NODE has been defined yet in the file

        *We don't consider node blocks as able to go beyond three lines.
        If a scenario like the following occurs, we won't even consider seq
        3 -- we'll get to seq 2 and consider the node as "done", ignoring
        seq 3 unless it starts with NODE or ARC.

        Line A. [NODE declaration]
        Line B. [seq 1]
        Line C. [seq 2]
        Line D. [seq 3]
    """
    header_num_nodes = 0
    num_nodes = 0
    in_node_block = False
    curr_node_id = None
    curr_node_fwdseq = None
    curr_node_length = 0
    line_num = 1
    seen_nodes = []
    for line in graph_file:
        if line_num == 1:
            header_num_nodes_str = line.split()[0]
            if not header_num_nodes_str.isdigit():
                raise ValueError(
                    "Line 1: $NUMBER_OF_NODES must be an integer value. "
                    "Currently, it's {}.".format(header_num_nodes_str)
                )
            header_num_nodes = int(header_num_nodes_str)

        if line.startswith("NODE\t"):
            if in_node_block:
                raise ValueError(
                    "Line {}: Node block ends too early.".format(line_num)
                )
            split_line = line.split()
            if len(split_line) < 4:
                raise ValueError(
                    "Line {}: Node declaration doesn't include enough "
                    "fields.".format(line_num)
                )
            if not split_line[2].isdigit() or not split_line[3].isdigit():
                raise ValueError(
                    "Line {}: The $COV_SHORT1 and $O_COV_SHORT1 values "
                    "must be integer values.".format(line_num)
                )
            if split_line[1][0] == "-":
                raise ValueError(
                    "Line {}: Node IDs can't start with "
                    "'-'.".format(line_num)
                )
            if split_line[1] in seen_nodes:
                raise ValueError(
                    "Line {}: Node ID {} declared multiple times.".format(
                        line_num, split_line[1]
                    )
                )
            # This node declaration seems tentatively ok.
            curr_node_id = split_line[1]
            curr_node_length = int(split_line[2])
            in_node_block = True
            num_nodes += 1

        elif line.startswith("ARC\t"):
            if in_node_block:
                raise ValueError(
                    "Line {}: Node block ends too early.".format(line_num)
                )
            split_line = line.split()
            if len(split_line) < 4:
                raise ValueError(
                    "Line {}: Arc declaration doesn't include enough "
                    "fields.".format(line_num)
                )
            if not split_line[2].isdigit():
                raise ValueError(
                    "Line {}: The $MULTIPLICITY value of an arc must be "
                    "an integer value.".format(line_num)
                )
            for node_id in split_line[1:3]:
                if node_id not in seen_nodes:
                    raise ValueError(
                        "Line {}: Unseen node {} referred to in an "
                        "arc.".format(line_num, node_id)
                    )
        elif in_node_block:
            if curr_node_fwdseq is None:
                curr_node_fwdseq = line.strip()
                if curr_node_length != len(curr_node_fwdseq):
                    raise ValueError(
                        "Line {}: Node sequence length doesn't match "
                        "$COV_SHORT1.".format(line_num)
                    )
            else:
                # The current line is the reverse sequence of this node.
                if len(curr_node_fwdseq) != len(line.strip()):
                    raise ValueError(
                        "Line {}: Node sequences have unequal "
                        "lengths.".format(line_num)
                    )
                # If we've made it here, we've seen all there is to see
                # about the current node block. We can say that this node
                # is tentatively valid (and we can add it to seen_nodes).
                seen_nodes.append(curr_node_id)
                seen_nodes.append(negate_node_id(curr_node_id))

                # Reset various flag variables
                in_node_block = False
                curr_node_id = None
                curr_node_length = 0
                curr_node_fwdseq = None
        line_num += 1
    # If we finished reading the file while we were *still* in a node
    # block, then that means that the file ended before a given node's
    # declaration did. That's a problem!
    if in_node_block:
        raise ValueError("Node block ended too early at end-of-file.")
    if len(seen_nodes) != (header_num_nodes * 2):
        raise ValueError(
            "The file's header indicated that there were {} nodes, but "
            "we identified {} nodes.".format(header_num_nodes, len(seen_nodes))
        )


def parse_gml(filename):
    return nx.gml.read_gml(filename)


def parse_gfa(filename):
    # NOTE: At present, we only care about segments (nodes) and links
    # (edges) in the GFA graph. A TODO is displaying all or most of the
    # relevant information in these graphs, like GfaViz does: see
    # https://github.com/marbl/MetagenomeScope/issues/147.
    digraph = nx.DiGraph()
    gfa_graph = gfapy.Gfa.from_file(filename)

    # Add nodes ("segments") to the DiGraph
    for node in gfa_graph.segments:
        if node.length is None:
            raise ValueError(
                "Found a node without a specified length: "
                "{}".format(node.name)
            )
        if node.name[0] == "-":
            raise ValueError(
                "Node IDs in the input assembly graph cannot "
                'start with the "-" character.'
            )
        sequence_gc = None
        if not gfapy.is_placeholder(node.sequence):
            sequence_gc = gc_content(node.sequence)[0]
        # Add both a positive and negative node.
        for name in (node.name, negate_node_id(node.name)):
            digraph.add_node(name, length=node.length, gc_content=sequence_gc)
    # Up front, make sure we're considering the complement of every edge
    gfa_edges_to_add = gfa_graph.edges
    for edge in gfa_graph.edges:
        gfa_edges_to_add.append(edge.complement())

    # Now, add edges to the DiGraph
    for edge in gfa_edges_to_add:
        src_id = edge.from_name
        tgt_id = edge.to_name
        if edge.from_orient == "-":
            src_id = negate_node_id(src_id)
        if edge.to_orient == "-":
            tgt_id = negate_node_id(tgt_id)
        digraph.add_edge(src_id, tgt_id)
    return digraph


def parse_fastg(filename):
    raise NotImplementedError(
        "FASTG support isn't done yet! Give me a few weeks!"
    )


def parse_lastgraph(filename):
    """Returns a nx.DiGraph representation of a LastGraph (Velvet) file.

    As far as I'm aware, there isn't a standard LastGraph parser available
    for Python. This function, then, just uses a simple line-by-line
    parser. It's not a very smart parser, so if your LastGraph file isn't
    "standard" (e.g. has empty lines between nodes), this will get messed
    up.

    Fun fact: this parser was the first part of MetagenomeScope I ever
    wrote! (I've updated the code since to be a bit less sloppy.)

    References
    ----------
    https://www.ebi.ac.uk/~zerbino/velvet/Manual.pdf
        Includes documentation of the LastGraph file format in section
        4.2.4.

    https://github.com/rrwick/Bandage
        The behavior of the LastGraph parser here (i.e. calculating depth
        as $O_COV_SHORT_1 / $COV_SHORT_1) was primarily based on chucking
        LastGraph files into Bandage and seeing how it handled them.
    """
    with open(filename, "r") as graph_file:
        attempt_to_validate_lastgraph_file(graph_file)
        # If attempt_to_validate_lastgraph_file() succeeded, we shouldn't have
        # any problems parsing this assembly graph.

        # Now, go back to the start of the file so we can actually *parse* it
        # this time, instead of just checking it for correctness.
        # CODELINK: https://stackoverflow.com/a/2106825/10730311
        graph_file.seek(0)
        digraph = nx.DiGraph()
        parsing_node = False
        parsed_fwdseq = False
        curr_node_attrs = {
            "id": "",
            "length": -1,
            "depth": -1,
            "fwdseq": None,
            "revseq": None,
        }
        for line in graph_file:
            if line.startswith("NODE"):
                parsing_node = True
                line_contents = line.split()
                curr_node_attrs["id"] = line_contents[1]
                if curr_node_attrs["id"][0] == "-":
                    raise ValueError(
                        "Node IDs in the input assembly graph cannot "
                        'start with the "-" character.'
                    )
                curr_node_attrs["length"] = int(line_contents[2])
                # NOTE: we define "depth" as just the node's O_COV_SHORT_1
                # value divided by the node's length (its COV_SHORT_1
                # value). This decision mirrors Bandage's behavior with
                # LastGraph files.
                curr_node_attrs["depth"] = (
                    float(line_contents[3]) / curr_node_attrs["length"]
                )
            elif line.startswith("ARC"):
                line_contents = line.split()
                id1, id2 = line_contents[1], line_contents[2]
                nid1 = negate_node_id(line_contents[1])
                nid2 = negate_node_id(line_contents[2])
                multiplicity = int(line_contents[3])
                digraph.add_edge(id1, id2, multiplicity=multiplicity)
                # Only add implied edge if the edge does not imply itself
                # (e.g. "ABC" -> "-ABC" or "-ABC" -> "ABC")
                if not (id1 == nid2 and id2 == nid1):
                    digraph.add_edge(nid2, nid1, multiplicity=multiplicity)
            elif parsing_node:
                if not parsed_fwdseq:
                    curr_node_attrs["fwdseq"] = line.strip()
                    # OK, now we've read in two lines: the first line of
                    # this node (describing general information), and the
                    # second line of this node (containing the forward
                    # sequence, a.k.a. $ENDS_OF_KMERS_OF_NODE). We can
                    # add a node for the "positive" node to the digraph.
                    digraph.add_node(
                        curr_node_attrs["id"],
                        length=curr_node_attrs["length"],
                        depth=curr_node_attrs["depth"],
                        gc_content=gc_content(curr_node_attrs["fwdseq"])[0],
                    )
                    parsed_fwdseq = True
                else:
                    curr_node_attrs["revseq"] = line.strip()
                    # Now we can add a node for the "negative" node.
                    digraph.add_node(
                        negate_node_id(curr_node_attrs["id"]),
                        length=curr_node_attrs["length"],
                        depth=curr_node_attrs["depth"],
                        gc_content=gc_content(curr_node_attrs["revseq"])[0],
                    )
                    # At this point, we're done with parsing this node.
                    # Clear our temporary variables for later use if
                    # parsing other nodes.
                    parsing_node = False
                    parsed_fwdseq = False
                    curr_node_attrs = {
                        "id": "",
                        "length": -1,
                        "depth": -1,
                        "fwdseq": None,
                        "revseq": None,
                    }
    return digraph


SUPPORTED_FILETYPE_TO_PARSER = {
    "lastgraph": parse_lastgraph,
    "gml": parse_gml,
    "gfa": parse_gfa,
    "fastg": parse_fastg,
}


def sniff_filetype(filename):
    """Attempts to determine the filetype of the file specified by a filename.

       Currently, this just returns the extension of the filename (after
       converting the filename to lowercase). If the extension isn't one of
       "lastgraph", "gfa", "fastg", or "gml", this throws a
       NotImplementedError.

       It might be worth extending this in the future to try sniffing via a
       more sophisticated method, but this seems fine for the time being.
    """
    lowercase_fn = filename.lower()
    for suffix in SUPPORTED_FILETYPE_TO_PARSER:
        if lowercase_fn.endswith(suffix):
            return suffix
    raise NotImplementedError(
        "The input filename ({}) doesn't end with one of the following "
        "supported filetypes: {}. Please provide an assembly graph that "
        "follows one of these filetypes and is named accordingly.".format(
            filename, tuple(SUPPORTED_FILETYPE_TO_PARSER.keys())
        )
    )


def parse(filename):
    filetype = sniff_filetype(filename)
    return SUPPORTED_FILETYPE_TO_PARSER[filetype](filename)
