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
# This should be very doable (and hopefully mostly-painless). You'll need to:
#
#  1. Create a function that takes as input a filename and (if the graph is
#  valid) returns a NetworkX DiGraph representing the contained assembly graph.
#
#  2. Add the lowercase file extension as a key in SUPPORTED_FILETYPE_TO_PARSER
#  that maps to your new function.
#
#  3. Add tests for your parser in metagenomescope/tests/assembly_graph_parser/

import networkx as nx
import gfapy
from .input_node_utils import gc_content, negate_node_id


def is_not_pos_int(number_string):
    """Returns False if a str represents a positive integer; True otherwise.

    (Also, if number_string is actually an int, this'll return False if it's
    a *positive* int. If number_string is actually a float, this'll immediately
    return True.)

    The behavior of this function is a tad bit confusing, so another way to
    think about it is "should we throw an error, given this input (which is
    supposed to represent a positive integer number)?"

    CODELINK: Note that we explicitly consider 0 as non-positive (i.e. "no,
    this is not ok and we should throw an error").
    I actually forgot about this corner case until looking over Bandage's
    LastGraph-parsing code (buildDeBruijnGraphFromLastGraph(), in
    https://github.com/rrwick/Bandage/blob/1fccd83c072f1e2b47191d144a6d38fdb69126d9/graph/assemblygraph.cpp)
    -- thanks to Torsten Seemann for the suggestion to look over that code.
    """
    if type(number_string) == int:
        return number_string <= 0
    elif type(number_string) == float:
        return True
    elif type(number_string) == str:
        # Due to boolean short-circuiting, the int() call won't happen if
        # not number_string.isdigit() is True
        return not number_string.isdigit() or int(number_string) <= 0
    else:
        # This isn't an int, float, or str. (It could be a list, as is the case
        # if the same attribute is specified twice for a given element.) Return
        # True -- this definitely isn't handleable as a positive integer.
        return True


def validate_lastgraph_file(graph_file):
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
    seen_edges = []
    for line in graph_file:
        if line_num == 1:
            header_num_nodes_str = line.split()[0]
            if is_not_pos_int(header_num_nodes_str):
                raise ValueError(
                    "Line 1: $NUMBER_OF_NODES must be a positive integer."
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
            if is_not_pos_int(split_line[2]) or is_not_pos_int(split_line[3]):
                raise ValueError(
                    "Line {}: The $COV_SHORT1 and $O_COV_SHORT1 values "
                    "must be positive integers.".format(line_num)
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
            if is_not_pos_int(split_line[3]):
                raise ValueError(
                    "Line {}: The $MULTIPLICITY value of an arc must be "
                    "a positive integer.".format(line_num)
                )
            for node_id in split_line[1:3]:
                # For reference, split_line[1:3] just gives you all the stuff
                # in the range [1, 3) (i.e. the second and third elements of
                # split_line, referring to the source and target node of this
                # edge)
                if node_id not in seen_nodes:
                    raise ValueError(
                        "Line {}: Unseen node {} referred to in an "
                        "arc.".format(line_num, node_id)
                    )
            fwd_ids = (split_line[1], split_line[2])
            rev_ids = (
                negate_node_id(split_line[2]),
                negate_node_id(split_line[1]),
            )
            # If rev_ids is in seen_edges, then so is fwd_ids. No need to check
            # both here.
            if fwd_ids in seen_edges:
                raise ValueError(
                    "Line {}: Edge from {} to {} somehow declared multiple "
                    "times.".format(line_num, split_line[1], split_line[2])
                )
            seen_edges.append(fwd_ids)
            seen_edges.append(rev_ids)
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
        # seen_nodes should always be divisible by 2 (since every time we
        # record a node we add it and its complement), so dividing
        # len(seen_nodes) by 2 is ok
        raise ValueError(
            "The file's header indicated that there were {} node(s), but "
            "we identified {} node(s).".format(
                header_num_nodes, int(len(seen_nodes) / 2)
            )
        )


def parse_metacarvel_gml(filename):
    """Returns a nx.DiGraph representation of a GML (MetaCarvel output) file.

    Unlike, say, LastGraph, the GML file spec isn't inherently tied to
    MetaCarvel (it's used by lots of different programs). However, we make the
    simplifying assumption that -- if you're trying to load in a GML file
    to MetagenomeScope -- that file was generated from MetaCarvel. Of course,
    if future assemblers/scaffolders can produce graphs that are also in GML,
    we'll need to modify this module to handle those graphs properly.

    Since NetworkX has a function for reading GML files built-in, the bulk of
    effort in this function is just spent validating that the nx.DiGraph
    produced follows the format we expect (i.e. has all the metadata we
    anticipate MetaCarvel output graphs having).
    """
    g = nx.gml.read_gml(filename)

    # Verify that the graph is directed and doesn't have duplicate edges
    if not g.is_directed():
        raise ValueError("The input graph should be directed.")
    if g.is_multigraph():
        raise ValueError("Multigraphs are unsupported in MetagenomeScope.")

    # Verify that all nodes have the properties we expect nodes in MetaCarvel
    # output graphs to have (orientation, length)
    num_nodes = len(g.nodes)
    for required_field in ("orientation", "length"):
        num_nodes_with_field = len(nx.get_node_attributes(g, required_field))
        if num_nodes_with_field < num_nodes:
            raise ValueError(
                'Only {} / {} nodes have "{}" given.'.format(
                    num_nodes_with_field, num_nodes, required_field
                )
            )

    # Verify that orientation and length types are good
    for n in g.nodes:
        orientation = g.nodes[n]["orientation"]
        if type(orientation) != str or orientation not in ("FOW", "REV"):
            raise ValueError(
                'Node {} has unsupported orientation "{}". Should be either '
                '"FOW" or "REV".'.format(n, orientation)
            )
        if is_not_pos_int(g.nodes[n]["length"]):
            raise ValueError(
                'Node {} has non-positive-integer length "{}".'.format(
                    n, g.nodes[n]["length"]
                )
            )

    # Verify that all edges have the properties we expect edges in MetaCarvel
    # output graphs to have (orientation, mean, stdev, bsize)
    # bsize is the most important of these (in my opinion), since it actually
    # impacts the visual display of edges in the viewer interface.
    num_edges = len(g.edges)
    for required_field in ("orientation", "mean", "stdev", "bsize"):
        num_edges_with_field = len(nx.get_edge_attributes(g, required_field))
        if num_edges_with_field < num_edges:
            raise ValueError(
                'Only {} / {} edges have "{}" given.'.format(
                    num_edges_with_field, num_edges, required_field
                )
            )

    for e in g.edges:
        if g.edges[e]["orientation"] not in ("EE", "EB", "BE", "BB"):
            raise ValueError(
                'Edge {} has unsupported orientation "{}". Should be one of '
                '"EE", "EB", "BE", or "BB".'.format(
                    e, g.edges[e]["orientation"]
                )
            )
        if is_not_pos_int(g.edges[e]["bsize"]):
            raise ValueError(
                'Edge {} has non-positive-integer bsize "{}".'.format(
                    e, g.edges[e]["bsize"]
                )
            )
        # NOTE: Yeah, this technically allows for NaN/Infinity values to pass
        # through (since float('nan') and float('inf'), etc. are both allowed
        # in Python). That being said: I don't think that matters? If
        # people request it, I can change this in the future. (From what I can
        # tell, MetaCarvel outputs mean/stdev values from python, so if we see
        # a NaN or +/- Infinity in the data then this will interpret it
        # as was originally intended.)
        for field in ("mean", "stdev"):
            try:
                float(g.edges[e][field])
            except Exception:
                # Rationale for using except Exception is analogous to what's
                # discussed in this comment thread:
                # https://github.com/biocore/LabControl/pull/585#discussion_r323413268
                raise ValueError(
                    'Edge {} has non-numeric {} "{}".'.format(
                        e, field, g.edges[e][field]
                    )
                )

    return g  # , ("orientation",), ("bsize", "orientation", "mean", "stdev")


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
        validate_lastgraph_file(graph_file)
        # If validate_lastgraph_file() succeeded, we shouldn't have any
        # problems parsing this assembly graph.

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
    "gml": parse_metacarvel_gml,
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
