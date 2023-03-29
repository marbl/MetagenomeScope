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

import re
import networkx as nx
import gfapy
import pyfastg
from .input_node_utils import gc_content, negate_node_id
from .errors import GraphParsingError


LJA_LFL_PATT = re.compile(r"([ACGT]) ?([0-9]+)\(([0-9\.]+)\)")


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
    GraphParsingError
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
                raise GraphParsingError(
                    "Line 1: $NUMBER_OF_NODES must be a positive integer."
                    "Currently, it's {}.".format(header_num_nodes_str)
                )
            header_num_nodes = int(header_num_nodes_str)

        if line.startswith("NODE\t"):
            if in_node_block:
                raise GraphParsingError(
                    "Line {}: Node block ends too early.".format(line_num)
                )
            split_line = line.split()
            if len(split_line) < 4:
                raise GraphParsingError(
                    "Line {}: Node declaration doesn't include enough "
                    "fields.".format(line_num)
                )
            if is_not_pos_int(split_line[2]) or is_not_pos_int(split_line[3]):
                raise GraphParsingError(
                    "Line {}: The $COV_SHORT1 and $O_COV_SHORT1 values "
                    "must be positive integers.".format(line_num)
                )
            if split_line[1][0] == "-":
                raise GraphParsingError(
                    "Line {}: Node IDs can't start with "
                    "'-'.".format(line_num)
                )
            if split_line[1] in seen_nodes:
                raise GraphParsingError(
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
                raise GraphParsingError(
                    "Line {}: Node block ends too early.".format(line_num)
                )
            split_line = line.split()
            if len(split_line) < 4:
                raise GraphParsingError(
                    "Line {}: Arc declaration doesn't include enough "
                    "fields.".format(line_num)
                )
            if is_not_pos_int(split_line[3]):
                raise GraphParsingError(
                    "Line {}: The $MULTIPLICITY value of an arc must be "
                    "a positive integer.".format(line_num)
                )
            for node_id in split_line[1:3]:
                # For reference, split_line[1:3] just gives you all the stuff
                # in the range [1, 3) (i.e. the second and third elements of
                # split_line, referring to the source and target node of this
                # edge)
                if node_id not in seen_nodes:
                    raise GraphParsingError(
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
                raise GraphParsingError(
                    "Line {}: Edge from {} to {} somehow declared multiple "
                    "times.".format(line_num, split_line[1], split_line[2])
                )
            seen_edges.append(fwd_ids)
            seen_edges.append(rev_ids)
        elif in_node_block:
            if curr_node_fwdseq is None:
                curr_node_fwdseq = line.strip()
                if curr_node_length != len(curr_node_fwdseq):
                    raise GraphParsingError(
                        "Line {}: Node sequence length doesn't match "
                        "$COV_SHORT1.".format(line_num)
                    )
            else:
                # The current line is the reverse sequence of this node.
                if len(curr_node_fwdseq) != len(line.strip()):
                    raise GraphParsingError(
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
        raise GraphParsingError("Node block ended too early at end-of-file.")
    if len(seen_nodes) != (header_num_nodes * 2):
        # seen_nodes should always be divisible by 2 (since every time we
        # record a node we add it and its complement), so dividing
        # len(seen_nodes) by 2 is ok
        raise GraphParsingError(
            "The file's header indicated that there were {} node(s), but "
            "we identified {} node(s).".format(
                header_num_nodes, int(len(seen_nodes) / 2)
            )
        )


def validate_nx_digraph(g, required_node_fields, required_edge_fields):
    # Verify that the graph is directed and doesn't have duplicate edges
    if not g.is_directed():
        raise GraphParsingError("The input graph should be directed.")
    if g.is_multigraph():
        raise GraphParsingError(
            "Multigraphs are unsupported in MetagenomeScope."
        )

    # Verify that all nodes have the properties we expect nodes to have
    num_nodes = len(g.nodes)
    for required_field in required_node_fields:
        num_nodes_with_field = len(nx.get_node_attributes(g, required_field))
        if num_nodes_with_field < num_nodes:
            raise GraphParsingError(
                'Only {} / {} nodes have "{}" given.'.format(
                    num_nodes_with_field, num_nodes, required_field
                )
            )

    # Verify that all edges have the properties we expect edges to have
    num_edges = len(g.edges)
    for required_field in required_edge_fields:
        num_edges_with_field = len(nx.get_edge_attributes(g, required_field))
        if num_edges_with_field < num_edges:
            raise GraphParsingError(
                'Only {} / {} edges have "{}" given.'.format(
                    num_edges_with_field, num_edges, required_field
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

    validate_nx_digraph(
        g,
        ("orientation", "length"),
        ("orientation", "mean", "stdev", "bsize"),
    )

    # Verify that node attributes are good. Also, change orientations from FOW
    # and REV to + and -, to standardize this across filetypes, and convert
    # lengths from strings to integers.
    for n in g.nodes:
        orientation = g.nodes[n]["orientation"]
        if type(orientation) != str or orientation not in ("FOW", "REV"):
            raise GraphParsingError(
                'Node {} has unsupported orientation "{}". Should be either '
                '"FOW" or "REV".'.format(n, orientation)
            )
        if is_not_pos_int(g.nodes[n]["length"]):
            raise GraphParsingError(
                'Node {} has non-positive-integer length "{}".'.format(
                    n, g.nodes[n]["length"]
                )
            )
        g.nodes[n]["orientation"] = "+" if orientation == "FOW" else "-"
        g.nodes[n]["length"] = int(g.nodes[n]["length"])

    # Verify that edge attributes are good
    for e in g.edges:
        if g.edges[e]["orientation"] not in ("EE", "EB", "BE", "BB"):
            raise GraphParsingError(
                'Edge {} has unsupported orientation "{}". Should be one of '
                '"EE", "EB", "BE", or "BB".'.format(
                    e, g.edges[e]["orientation"]
                )
            )
        if is_not_pos_int(g.edges[e]["bsize"]):
            raise GraphParsingError(
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
        # as was originally intended.) Unlike bsize, we don't really use "mean"
        # or "stdev" for anything at present, so there isn't a risk of us e.g.
        # scaling edges by their stdev and then having an edge with an
        # "infinity" stdev just explode everything
        for field in ("mean", "stdev"):
            try:
                float(g.edges[e][field])
            except Exception:
                # Rationale for using except Exception is analogous to what's
                # discussed in this comment thread:
                # https://github.com/biocore/LabControl/pull/585#discussion_r323413268
                raise GraphParsingError(
                    'Edge {} has non-numeric {} "{}".'.format(
                        e, field, g.edges[e][field]
                    )
                )

    return g  # , ("orientation",), ("bsize", "orientation", "mean", "stdev")


def parse_gfa(filename):
    """Returns a nx.DiGraph representation of a GFA1 or GFA2 file.

    NOTE that, at present, we only visualize nodes and edges in the GFA graph.
    A TODO is displaying all or most of the relevant information in these
    graphs, like GfaViz does: see
    https://github.com/marbl/MetagenomeScope/issues/147 for discussion of this.
    """
    digraph = nx.DiGraph()
    gfa_graph = gfapy.Gfa.from_file(filename)

    # Add nodes ("segments") to the DiGraph
    for node in gfa_graph.segments:
        if node.length is None:
            raise GraphParsingError(
                "Found a node without a specified length: "
                "{}".format(node.name)
            )
        if node.name[0] == "-":
            raise GraphParsingError(
                "Node IDs in the input assembly graph cannot "
                'start with the "-" character.'
            )
        sequence_gc = None
        if not gfapy.is_placeholder(node.sequence):
            sequence_gc = gc_content(node.sequence)[0]
        # Add both a positive and negative node.
        digraph.add_node(
            node.name,
            length=node.length,
            gc_content=sequence_gc,
            orientation="+",
        )
        digraph.add_node(
            negate_node_id(node.name),
            length=node.length,
            gc_content=sequence_gc,
            orientation="-",
        )

    # Now, add edges to the DiGraph
    for edge in gfa_graph.edges:
        # Set edge_tuple to the edge's explicitly specified orientation
        # This code is a bit verbose, but that was the easiest way to write it
        # I could think of
        if edge.from_orient == "-":
            src_id = negate_node_id(edge.from_name)
        else:
            src_id = edge.from_name
        if edge.to_orient == "-":
            tgt_id = negate_node_id(edge.to_name)
        else:
            tgt_id = edge.to_name
        edge_tuple = (src_id, tgt_id)
        digraph.add_edge(*edge_tuple)

        # Now, try to add the complement of the edge (done manually, since
        # .complement() isn't available for GFA2 edges as of writing)
        complement_tuple = (negate_node_id(tgt_id), negate_node_id(src_id))

        # Don't add an edge twice if its complement is itself (as in the
        # loop.gfa test case)
        if complement_tuple != edge_tuple:
            digraph.add_edge(*complement_tuple)
    return digraph


def parse_fastg(filename):
    g = pyfastg.parse_fastg(filename)
    validate_nx_digraph(g, ("length", "cov", "gc"), ())
    # Add an "orientation" attribute for every node.
    # pyfastg guarantees that every node should have a +/- suffix assigned to
    # its name, so this should be safe.
    for n in g.nodes:
        suffix = n[-1]
        if suffix == "+":
            g.nodes[n]["orientation"] = "+"
        elif suffix == "-":
            g.nodes[n]["orientation"] = "-"
        else:
            raise GraphParsingError(
                (
                    "Node {} in parsed FASTG file doesn't have an "
                    "orientation?"
                ).format(n)
            )
    return g


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
                        orientation="+",
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
                        orientation="-",
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


def parse_dot(filename):
    """Returns a nx.MultiDiGraph representation of a DOT (Graphviz) file.

    Like GML files, DOT is a file format for representing arbitrary graphs (not
    just assembly graphs). Furthermore, multiple assemblers output DOT files
    (and may encode biological information like sequence lengths in different
    ways in this file).

    Here, I limit our scope to visualizing DOT files produced by LJA / jumboDBG
    or Flye. I'm sure there are other assemblers that can create DOT files,
    but -- to keep the scope of this parser reasonable for the time being -- I
    will just focus on these specific assemblers' output DOT files.
    """
    # This function is recommended by NetworkX over the nx.nx_pydot version;
    # see https://networkx.org/documentation/stable/_modules/networkx/drawing/nx_pydot.html#read_dot
    # (Also, the nx_agraph version only requires pygraphviz, which we should
    # already have installed.)
    g = nx.nx_agraph.read_dot(filename)

    # For both LJA and Flye DOT files, the main attributes we care about are
    # stored in the edge labels.
    #
    # LJA's edge labels look like "A1235(5)", which indicates that this edge
    # starts with an A nucleotide, has a length of 1,235 nt, and has a
    # multiplicity (average coverage of k-mers in this edge by reads) of 5x.
    #
    # And Flye's edge labels look like "id 5678\l50k 5x", which indicates that
    # this edge has an ID of "5678", a length of ~50kbp, and a coverage of 5x.
    # (The lengths are approximate -- see
    # https://github.com/fenderglass/Flye/blob/3f0154aed48d006b1387cf39918c7c05236cdcdd/src/repeat_graph/output_generator.cpp#L303-L312
    # for the exact logic, as of writing. I don't think this is a huge deal,
    # but maybe we should add a warning somewhere.)

    # One -- and ONLY one of these -- should be True, after considering all
    # edges in the graph.
    lja_vibes = False
    flye_vibes = False
    seen_one_edge = False

    for e in g.edges(data=True, keys=True):
        seen_one_edge = True
        err_prefix = f"Edge {e[0]} -> {e[1]}"

        if "label" not in e[3]:
            raise GraphParsingError(
                f"{err_prefix} has no label. Note that we currently only "
                "accept Graphviz files from Flye or LJA / jumboDBG."
            )

        # Both Flye and LJA DOT files have edge labels. Use this label to
        # figure out which type of graph this is.
        label = e[3]["label"]
        if label.startswith("id"):
            if lja_vibes:
                raise GraphParsingError(
                    f"{err_prefix} looks like it came from Flye, but other "
                    "edges in the same file look like they came from LJA?"
                )
            if "\\l" not in label:
                raise GraphParsingError(
                    f"{err_prefix} has a label that looks like it came from "
                    "Flye, but doesn't include a '\\l' separator."
                )
            parts = label.split("\\l")
            if len(parts) != 2:
                # This is kind of untrue -- there are other newline separators
                # that Graphviz accepts
                # (https://graphviz.org/docs/attr-types/escString/) -- but we
                # can assume that only \l will be used since that's what Flye
                # uses (at the moment).
                raise GraphParsingError(
                    f"{err_prefix} has a label that seems like it spans != 2 "
                    "lines?"
                )

            # Get the edge ID
            id_part = parts[0]
            id_parts = id_part.split()
            if len(id_parts) != 2:
                raise GraphParsingError(
                    f"{err_prefix} has a label where the first line is "
                    f"{id_part}. There should be a single space character "
                    "between the word 'id' and the actual ID, and the ID "
                    "shouldn't contain any whitespace."
                )
            eid = id_parts[1]

            # Get the length and coverage
            lencov_part = parts[1]
            lencov_parts = lencov_part.split()
            if len(lencov_parts) != 2:
                raise GraphParsingError(
                    f"{err_prefix} has a label where the second line is "
                    f"{lencov_part}. It should contain just the edge length "
                    "and coverage, separated by a single space character."
                )
            elen_str, ecov_str = lencov_parts
            # Get the length
            if elen_str.isdigit():
                # I don't think Flye outputs lengths in this style, but we
                # might as well be nice and accept lengths that are formatted
                # like this if this ever changes
                elen = int(elen_str)
            else:
                if elen_str[-1] == "k":
                    # This will fail if the first part of the length string
                    # (before the "k") isn't a valid float. I think letting
                    # this error go up to the end user is fine -- this should
                    # never happen anyway, since if we've made it this far this
                    # is almost certainly a real Flye assembly graph.
                    elen_thousands = float(elen_str[:-1])
                    # Of course, this is just an approximation of the *true*
                    # edge length. Something we may want to warn about, as
                    # discussed above.
                    elen = elen_thousands * 1000
                else:
                    raise GraphParsingError(
                        f"{err_prefix} has a confusing length of {elen_str}?"
                    )

            # Get the coverage -- this should just be a rounded integer ending
            # in "x", so it's easier for us to parse than the length.
            if ecov_str.isdigit():
                # Again, I don't think Flye should output coverages that lack
                # the "x", but it's easy to account for this case and parse 'em
                # anyway
                ecov = int(ecov_str)
            else:
                if ecov_str[-1] == "x":
                    # This can fail if the coverage isn't a valid int, but
                    # that's fine -- just let the error go up to the user
                    ecov = int(ecov_str[:-1])
                else:
                    raise GraphParsingError(
                        f"{err_prefix} has a confusing coverage of {ecov_str}?"
                    )

            # If we've made it here, then we've successfully read the ID,
            # length, and coverage of this edge. Save it, and (if we haven't
            # already) record that this is probably a Flye assembly graph.
            g.edges[e[:3]]["id"] = eid
            g.edges[e[:3]]["approx_length"] = elen
            g.edges[e[:3]]["cov"] = ecov
            # We've now extracted, as far as I can tell, all of the information
            # contained in Flye's edge labels. Let's remove this label from the
            # edge data -- showing it to the user would be redundant.
            del e[3]["label"]
            # Also, remove the penwidth attr, which flye assigns to repetitive
            # (?) edges -- we already keep the "color" attr around for these
            # edges, which I believe should be sufficient. And I don't want to
            # confuse this with the edge thickness scaling for coverages.
            if "penwidth" in e[3]:
                del e[3]["penwidth"]
            flye_vibes = True
        else:
            if flye_vibes:
                raise GraphParsingError(
                    f"{err_prefix} looks like it came from LJA, but other "
                    "edges in the same file look like they came from Flye?"
                )
            label_first_line = label.splitlines()[0]
            lfl_match = re.match(LJA_LFL_PATT, label_first_line)
            if lfl_match is None:
                raise GraphParsingError(
                    f"{err_prefix} has a label with a confusing first line, "
                    "at least for LJA edge labels."
                )

            groups = lfl_match.groups()

            # The length and kmer-cov lines could cause errors if these aren't
            # valid numbers. That's fine -- like in the Flye parser, let the
            # errors propagate up to the user.
            g.edges[e[:3]]["first_nt"] = groups[0]
            g.edges[e[:3]]["length"] = int(groups[1])
            g.edges[e[:3]]["kmer_cov"] = float(groups[2])

            # Both Flye and LJA give all edges "color" attributes in these DOT
            # files. As far as I can tell, Flye will color edges if they are
            # special (e.g. repeats, according to Flye?), while LJA will just color
            # all edges black. For now, we preserve "color" for Flye edges,
            # but delete this info for LJA edges.
            if "color" in e[3]:
                # It turns out that the "data" object returned by g.edges()
                # is still linked to the "graph"'s version of this data -- we can
                # modify e[3] directly here to remove this. (Previously, I was
                # thinking we'd have to say "del g.edges[e[:3]]["color"]".)
                del e[3]["color"]

            # The full label could be useful for the visualization. LJA can
            # generate labels spanning multiple lines (although jumboDBG's
            # labels seem mostly to span single lines). So, we will not delete
            # this label from the edge data.
            lja_vibes = True

    if not seen_one_edge:
        # For "node-major" graphs I guess this is ok. For de Bruijn graphs,
        # though, we are going to have problems. Probably.
        raise GraphParsingError("DOT-format graph contains 0 edges.")

    # Only one of these should be True. ("^" is the XOR operator in Python.)
    # I thiiiink this case will only get triggered if, uh, there aren't any
    # edges in the graph. But I'm keeping this here just in case I messed
    # something up.
    if not (lja_vibes ^ flye_vibes):
        raise GraphParsingError("Call a priest. Something went wrong.")

    # Both Flye and LJA DOT files, as of writing, provide some cosmetic
    # node-specific attributes ("style" = "filled", "fillcolor" = either "grey"
    # (Flye) or "white" (LJA)) which I don't think we need to care about here.
    # (In all the Flye / LJA example DOT files I've seen these are uniform for
    # all nodes in the graph.) Maybe, if there are differences between nodes
    # within a graph, we could pass these on to the visualization, but I don't
    # think that's needed yet.) To limit confusion and save space, we delete
    # these attributes here.
    for n in g.nodes:
        if "style" in g.nodes[n]:
            del g.nodes[n]["style"]
        if "fillcolor" in g.nodes[n]:
            del g.nodes[n]["fillcolor"]

    return g


# Multiple suffixes can point to the same parser -- for example, both .gv and
# .dot are often used for Graphviz files. (See
# https://en.wikipedia.org/wiki/DOT_(graph_description_language) and its
# references for some details.)
SUPPORTED_FILETYPE_TO_PARSER = {
    "lastgraph": parse_lastgraph,
    "gml": parse_metacarvel_gml,
    "gfa": parse_gfa,
    "fastg": parse_fastg,
    "gv": parse_dot,
    "dot": parse_dot,
}


def sniff_filetype(filename):
    """Attempts to determine the filetype of the file specified by a filename.

    Currently, this just returns the extension of the filename (after
    converting the filename to lowercase). If the lowercase'd extension isn't
    listed as a key in SUPPORTED_FILETYPE_TO_PARSER, then this will throw a
    NotImplementedError.

    It might be worth extending this in the future to try sniffing via more
    sophisticated methods (i.e. actually checking the first few characters in
    these files), but this is a fine (albeit inelegant) solution for now.
    """
    lowercase_fn = filename.lower()
    for suffix in SUPPORTED_FILETYPE_TO_PARSER:
        if lowercase_fn.endswith(suffix):
            return suffix
    allowed_suffixes = (
        "{"
        + ", ".join(f'"{s}"' for s in SUPPORTED_FILETYPE_TO_PARSER.keys())
        + "}"
    )
    raise NotImplementedError(
        f"The input filename ({filename}) doesn't end with one of the "
        f"following supported filetype suffixes: {allowed_suffixes}. Please "
        "provide an assembly graph that (i) follows one of these file formats "
        "and (ii) has a filename that ends with the corresponding filetype "
        "suffix."
    )


def parse(filename):
    filetype = sniff_filetype(filename)
    return SUPPORTED_FILETYPE_TO_PARSER[filetype](filename)
