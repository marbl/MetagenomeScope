# This module contains various utility functions for parsing assembly graph
# files. All of the parse_() functions here should return a NetworkX
# MultiDiGraph representing the assembly graph in the input file, assuming the
# input file is "valid."
#
# You can also just call parse(), which will attempt to determine which parser
# to use on your file based on its extension.
#
###############################################################################
# ADDING SUPPORT FOR MORE ASSEMBLY GRAPH FILETYPES
###############################################################################
#
# This should be very doable (and hopefully mostly-painless). You'll need to:
#
#  1. Create a function that takes as input a filename and (if the graph is
#  valid) returns a NetworkX MultiDiGraph representing the contained assembly
#  graph. (You can make it return other stuff in addition to the graph if
#  desired, but then you'll need to modify the AssemblyGraph __init__()
#  function to account for that.)
#
#  2. Add the lowercase file extension as a key in SUPPORTED_FILETYPE_TO_PARSER
#  that maps to your new function.
#
#  3. Update the following config variables in this file regarding your
#  filetype:
#      - FILETYPE2HR (what is the "human-readable" name of your filetype?)
#      - HRFILETYPE2NODECENTRIC (are sequences on nodes or on edges?)
#      - HRFILETYPE2ORIENTATION_IN_NAME (are orientations encoded in names?)
#
#  4. Add tests for your parser in metagenomescope/tests/parsers/

import re
import logging
import networkx as nx
import gfapy
import pyfastg
from . import config
from .name_utils import negate
from .seq_utils import gc_content
from .errors import GraphParsingError, WeirdError

LJA_LFL_PATT = re.compile(
    r"([\-_a-zA-Z\d\.]+) ([ACGT]) ?([0-9]+)\(([0-9\.]+)\)"
)


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
    if type(number_string) is int:
        return number_string <= 0
    elif type(number_string) is float:
        return True
    elif type(number_string) is str:
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
        If any of the following conditions hold in the file:

        General:
        -The $NUMBER_OF_NODES in the file header does not equal the number
         of NODE declarations in the file

        Any NODE:
        -doesn't have a $NODE_ID, $COV_SHORT1, and $O_COV_SHORT1 value
        -has a $NODE_ID that starts with a config.REV character
        -shares a $NODE_ID with another node in the same file
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
            if split_line[1][0] == config.REV:
                raise GraphParsingError(
                    f"Line {line_num}: Node IDs can't start with "
                    f"'{config.REV}'."
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
            rev_ids = (negate(split_line[2]), negate(split_line[1]))
            # NOTE: We could say "if fwd_ids in seen_edges" to check if this
            # edge has already been defined earlier in the file (if we wanted
            # to disallow multigraphs). Note that we would only need to check
            # if fwd_ids is present in seen_edges, rather than also checking
            # rev_ids, since these things are added in pairs (so the presence
            # of one implies the other). ... That all being said, we want to
            # allow multigraphs now! (In the futuristic days of, uh, 2023.
            # Jesus.) So, we don't trigger an error here.
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
                seen_nodes.append(negate(curr_node_id))

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


def make_multigraph_if_not_already(g):
    """Converts a nx.DiGraph to a nx.MultiDiGraph, if needed.

    Also, raises an error if the input graph is not a nx.DiGraph or a
    nx.MultiDiGraph. (This could happen if you have an undirected graph, I
    guess -- that's a big no-no for us, at least right now.)
    """
    if type(g) is nx.DiGraph:
        return nx.MultiDiGraph(g)
    elif type(g) is nx.MultiDiGraph:
        # we don't need to do anything
        return g
    else:
        raise WeirdError(
            f"Graph isn't a (Multi)DiGraph: it's of type {type(g)}?"
        )


def parse_metacarvel_gml(filename):
    """Returns a nx.MultiDiGraph representation of a MetaCarvel GML file.

    Unlike, say, LastGraph (which I'm pretty sure is only used by Velvet),
    the GML file spec isn't inherently tied to MetaCarvel; lots of different
    programs can produce and consume GML files. However, we make the
    simplifying assumption that -- if you're trying to load in a GML file
    to MetagenomeScope -- that file was generated from MetaCarvel. Of course,
    if future assemblers/scaffolders can produce graphs that are also in GML,
    we'll need to modify this module to handle those graphs properly. But I
    doubt that that will happen any time soon.

    Since NetworkX has a function for reading GML files built-in, the bulk of
    effort in this function is just spent validating that the nx.(Multi)DiGraph
    produced by NetworkX's reader follows the format we expect (i.e. it has all
    the node and edge attributes we anticipate MetaCarvel graphs having).

    Notes
    -----
    Nodes in GML files are expected (by nx.gml.read_gml()) to have both "id"
    and "label" fields. Furthermore, both of these should apparently be unique
    (no two nodes in the same file should have the same ID or label). By
    default, nx.gml.read_gml() will name nodes according to their label; node
    IDs won't actually be visible to us. This is fine, since (in MetaCarvel
    outputs) node labels seem to be more important than IDs.
    """
    g = nx.gml.read_gml(filename)

    validate_nx_digraph(
        g,
        ("orientation", "length"),
        ("orientation", "mean", "stdev", "bsize"),
    )

    # nx.gml.read_gml() returns graphs of variable types, depending on the
    # "directed" and "multigraph" flags in the first few lines of the file (and
    # maybe some other things, idk). But the important thing is -- we want to
    # make sure we return a nx.MultiDiGraph object from here, even if the graph
    # contains (for now) no parallel edges.
    g = make_multigraph_if_not_already(g)

    # Verify that node attributes are good. Also, change orientations from FOW
    # and REV to + and - (controlled by config.FWD / REV) to standardize this
    # across filetypes, and convert lengths from strings to integers.
    for n in g.nodes:
        orientation = g.nodes[n]["orientation"]
        if type(orientation) is not str or orientation not in ("FOW", "REV"):
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
        g.nodes[n]["orientation"] = (
            config.FWD if orientation == "FOW" else config.REV
        )
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
            datum = g.edges[e][field]
            # Some MetaCarvel graphs I have lying around encase the "mean"
            # values in quotes, which causes nx to parse them as strings and
            # later breaks their display in the selected element table. Let's
            # just cast them to floats up front.
            if type(datum) not in (float, int):
                try:
                    f = float(datum)
                except Exception:
                    # Rationale for using except Exception is analogous to
                    # what's discussed in this comment thread:
                    # https://github.com/biocore/LabControl/pull/585#discussion_r323413268
                    raise GraphParsingError(
                        f'Edge {e} has non-numeric {field} "{datum}".'
                    )
                g.edges[e][field] = f

    return g  # , ("orientation",), ("bsize", "orientation", "mean", "stdev")


def parse_gfa(filename):
    """Returns a nx.MultiDiGraph representation of a GFA1 or GFA2 file.

    Parameters
    ----------
    filename: str
        Path to a GFA1 / GFA2 file.

    Returns
    -------
    graph, paths: nx.MultiDiGraph, dict or None
        If this graph contains any paths (i.e. P-lines in GFA 1 files or
        O-lines in GFA 2 files), then "paths" will be a dict mapping path names
        to the names of nodes in the paths. Otherwise "paths" will be None.

    Notes
    -----
    - Although this returns an object of type nx.MultiGraph, it won't actually
      contain any parallel edges. This is because, as of writing, GfaPy will
      throw a NotUniqueError if you to have it read a GFA file containing
      duplicate link lines.

    - Currently we only store information about nodes (segments), edges
      (but not containments), and paths. Things like gaps, unoriented groups,
      and fragments (G-/U-/F- lines in GFA2) are ignored (at least for now).
      See https://github.com/marbl/MetagenomeScope/issues/147.

    - Regarding containments, see the comment below. We could visualize
      these but it will require some thinking to do it in a non-misleading
      way. See https://github.com/marbl/MetagenomeScope/commit/72bd908b6875d5fe0d4d7ae8674ea00821ace7d9
      for one way of doing this (but this has pitfalls because it just
      treats the containments like regular edges...)
    """
    digraph = nx.MultiDiGraph()
    gfa_graph = gfapy.Gfa.from_file(filename)

    # Add nodes ("segments") to the graph
    for node in gfa_graph.segments:
        if node.length is None:
            raise GraphParsingError(
                f"Found a node without a specified length: {node.name}"
            )
        if node.name[0] == config.REV:
            raise GraphParsingError(
                "Node IDs in the input assembly graph cannot "
                f'start with the "{config.REV}" character.'
            )
        sequence_gc = None
        if not gfapy.is_placeholder(node.sequence):
            sequence_gc = gc_content(node.sequence)[0]
        # If this sequence doesn't have an RC / KC / FC tag, then this will be
        # None. If all the coverages are None then the AssemblyGraph code
        # should detect that and not list coverages in the selected node table
        cov = node.coverage()
        # Add both a positive and negative node.
        digraph.add_node(
            node.name,
            length=node.length,
            gc_content=sequence_gc,
            orientation=config.FWD,
            cov=cov,
        )
        digraph.add_node(
            negate(node.name),
            length=node.length,
            gc_content=sequence_gc,
            orientation=config.REV,
            cov=cov,
        )

    # Now, add edges to the DiGraph
    for edge in gfa_graph.edges:

        # We could visualize containments if desired -- GfaViz does by drawing
        # a line between the nodes that connects in the middles of the nodes
        # rather than on the ends -- but since we don't support that sort of
        # functionality yet, i think it makes sense to ignore these for now
        # (like Bandage does from what i've seen)
        #
        # This is also complicated by how, like, containments are generally
        # listed in gfa 1 files as "container" -> "contained", so does it
        # make sense for a containment edge to have a RC? what would that
        # mean? it gets complicated
        if edge.is_containment():
            continue

        # Set edge_tuple to the edge's explicitly specified orientation
        # This code is a bit verbose, but that was the easiest way to write it
        # I could think of
        if edge.from_orient == config.REV:
            src_id = negate(edge.from_name)
        else:
            src_id = edge.from_name
        if edge.to_orient == config.REV:
            tgt_id = negate(edge.to_name)
        else:
            tgt_id = edge.to_name
        edge_tuple = (src_id, tgt_id)
        digraph.add_edge(*edge_tuple)

        complement_tuple = (negate(tgt_id), negate(src_id))

        # Don't add an edge twice if its complement is itself (as in the
        # loop.gfa test case)
        if complement_tuple != edge_tuple:
            digraph.add_edge(*complement_tuple)

    paths = None
    if len(gfa_graph.paths) > 0:
        paths = {}
        for p in gfa_graph.paths:
            # we make two versions of each path (one for each strand), which i
            # think matches the intent here
            rc_path_name = negate(p.name)
            # Gfapy should catch cases where two paths have the same name,
            # but there can be jank where a path's negated name is not unique.
            # Anyway let's just be paranoid and check
            if p.name in paths or rc_path_name in paths:
                raise GraphParsingError(f"Duplicate path ID: {p.name}")
            segments = []
            rc_segments = []
            for s in p.captured_segments:
                name = s.name
                rc_name = negate(name)
                if s.orient == config.FWD:
                    segments.append(name)
                    rc_segments.insert(0, rc_name)
                else:
                    segments.append(rc_name)
                    rc_segments.insert(0, name)
            if len(segments) == 0:
                logging.warning(
                    f"Path ({p.name}) contains zero segments. We don't "
                    "yet support creating GFA edge paths, so we are ignoring "
                    "it. If this is an important use-case to you, please let "
                    "us know on GitHub!"
                )
            else:
                paths[p.name] = segments
                paths[negate(p.name)] = rc_segments
        if len(paths) == 0:
            paths = None

    return digraph, paths


def parse_fastg(filename):
    """Returns a nx.MultiDiGraph representation of a FASTG file.

    We delegate most of this work to the pyfastg library
    (https://github.com/fedarko/pyfastg).

    Notes
    -----
    Although this returns an object of type nx.MultiGraph, it won't actually
    contain any parallel edges. This is because, as of writing, the latest
    pyfastg version (0.2.0) will throw an error if you try to use it to parse
    a multigraph. See https://github.com/fedarko/pyfastg/issues/8. This
    probably isn't a big deal, since I don't think SPAdes or MEGAHIT generate
    multigraph FASTG files. In any case, if people want us to support
    multigraph FASTG files, then we'd just need to update pyfastg (and then the
    rest of this function shouldn't need to change).
    """
    g = pyfastg.parse_fastg(filename)
    validate_nx_digraph(g, ("length", "cov", "gc"), ())
    g = make_multigraph_if_not_already(g)
    # Add an "orientation" attribute for every node.
    # pyfastg guarantees that every node should have a +/- suffix assigned to
    # its name, so this should be safe.
    #
    # Also, rename nodes: from N+ / N- to N / -N. The distinction doesn't
    # really matter much, but the other parsers name nodes in the latter way,
    # so we can be consistent.
    oldname2newname = {}
    for n in g.nodes:
        suffix = n[-1]
        if suffix == config.FWD:
            g.nodes[n]["orientation"] = config.FWD
            oldname2newname[n] = n[:-1]
        elif suffix == config.REV:
            g.nodes[n]["orientation"] = config.REV
            oldname2newname[n] = config.REV + n[:-1]
        else:
            # shouldn't happen, unless pyfastg breaks or changes its behavior
            # (but it's useful to have this check anyway, just to make this
            # bulletproof in case i forget and break something later lol)
            raise WeirdError(
                f"Node {n} in parsed FASTG file doesn't have an orientation?"
            )
    g = nx.relabel_nodes(g, oldname2newname)
    return g


def parse_lastgraph(filename):
    """Returns a nx.MultiDiGraph representation of a LastGraph (Velvet) file.

    As far as I'm aware, there isn't a standard LastGraph parser available
    for Python. This function, then, just uses a simple line-by-line
    parser. It's not a very smart parser, so if your LastGraph file isn't
    "standard" (e.g. has empty lines between nodes), this will get messed
    up.

    Fun fact: this parser was the first part of MetagenomeScope I ever
    wrote! (I've updated the code since to be a bit less sloppy.)

    Notes
    -----
    I haven't actually seen any LastGraph files that are multigraphs (you know,
    besides the files I've made up for testing). Returning a MultiDiGraph
    instead of a DiGraph might be overkill, then. (But we can definitely
    introduce parallel edges later on during pattern collapsing, so it's good
    to keep this around for now.)

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
        digraph = nx.MultiDiGraph()
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
                nid1 = negate(line_contents[1])
                nid2 = negate(line_contents[2])
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
                        orientation=config.FWD,
                    )
                    parsed_fwdseq = True
                else:
                    curr_node_attrs["revseq"] = line.strip()
                    # Now we can add a node for the "negative" node.
                    digraph.add_node(
                        negate(curr_node_attrs["id"]),
                        length=curr_node_attrs["length"],
                        depth=curr_node_attrs["depth"],
                        gc_content=gc_content(curr_node_attrs["revseq"])[0],
                        orientation=config.REV,
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

    Notes
    -----
    - Like GML, DOT is a file format for representing arbitrary graphs (not
      just assembly graphs). Furthermore, multiple assemblers output DOT files
      (and may encode biological information like sequence lengths in different
      ways in this file).

      Here, I limit our scope to visualizing DOT files produced by LJA /
      jumboDBG or Flye. I'm sure there are other assemblers that can create DOT
      files, but -- to keep the scope of this parser reasonable for now -- I
      will just focus on these specific assemblers' output DOT files.

    - In Flye DOT files, nodes don't seem to have orientations but edges do.
      In LJA DOT files, edges don't seem to have orientations but nodes do.
      Since "orientation" arguably isn't important for the direct visualization
      of de Bruijn graphs (I mean, we still keep the IDs that may or may not
      start with "-" around), I don't assign an "orientation" field to either
      nodes or edges in DOT files. I can change this if desired.

    - In the pathological case where the same node is defined twice (this can
      happen in LJA / jumboDBG outputs, as of writing, due to node IDs in the
      visualizations being truncations of longer IDs), then we won't actually
      notice this here -- since we defer to nx.nx_agraph.read_dot() to process
      the graph. It's important for the user to provide a graph where nodes
      all have unique IDs. (You can check LJA / jumboDBG graphs for this
      using https://gist.github.com/fedarko/dffb649120dbb2040da502cc5a4eb566,
      at least as of writing.)
    """
    # This function is recommended by NetworkX over the nx.nx_pydot version;
    # see https://networkx.org/documentation/stable/_modules/networkx/drawing/nx_pydot.html#read_dot
    # (Also, the nx_agraph version only requires pygraphviz, which we should
    # already have installed.)
    g = nx.nx_agraph.read_dot(filename)

    # Silly corner-case: giving NX's read_dot() a DOT file that starts with
    # "strict" will result in us getting a NetworkX DiGraph (not a
    # MultiDiGraph) object. We *could* just cast the graph to a MultiDiGraph,
    # but I worry about potential data loss in this way (e.g. NX silently
    # removing multi-edges); so, we force the user to give us good graphs.
    if type(g) is not nx.MultiDiGraph:
        raise GraphParsingError(
            "It looks like the input DOT file isn't a multi-digraph. This is "
            "probably due to one or both of the following: (1) the DOT file "
            'labels the graph as a "graph" instead of a "digraph," thus '
            "making it undirected; and/or (2) the DOT file starts with the "
            '"strict" keyword, which disallows parallel edges. Please adjust '
            "your DOT file accordingly."
        )

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

    seen_flye_edge_ids = set()

    for e in g.edges(data=True, keys=True):
        seen_one_edge = True
        err_prefix = f"Edge {e[0]} -> {e[1]}"

        if "label" not in e[3]:
            raise GraphParsingError(
                f"{err_prefix} has no label. Note that we currently only "
                "accept DOT files from Flye or LJA."
            )

        # if you import a graph using nx and then write it out then it
        # will include key attributes -- which will be set to strings
        # of '0' or something when reading this back in using nx. yuck.
        # maybe we should just silently ignore these keys in the future?
        # (or issue a warning?) but i feel more comfortable just loudly
        # crashing. if this actually impacts anyone in the future we can
        # handle it specially.
        #
        # (there are a couple places in the code that assume that keys
        # are 0-based integers, and i don't think it is worth updating
        # all of those right now to satisfy a corner case that will probs
        # never happen in practice)
        if type(e[2]) is not int:
            raise GraphParsingError(
                f"{err_prefix} has a non-int key (probably it is already "
                "set in the file -- did you export this graph using nx?) "
                "This will cause problems. We can support this case if "
                "needed, but for now I suggest removing explicitly-set "
                "keys from your graph."
            )

        # Both Flye and LJA DOT files have edge labels. Use this label to
        # figure out which type of graph this is.
        label = e[3]["label"]
        if label.startswith("id"):
            if lja_vibes:
                raise GraphParsingError(
                    f"{err_prefix} looks like it came from Flye, but other "
                    "edge(s) in the same file look like they came from LJA?"
                )
            if "\\l" not in label:
                raise GraphParsingError(
                    f"{err_prefix} has a label containing zero '\\l' "
                    "separators?"
                )
            parts = label.split("\\l")
            if len(parts) > 2:
                # Note that there are other newline separators besides \l that
                # Graphviz accepts (graphviz.org/docs/attr-types/escString/) --
                # but we can assume that only \l will be used since that's what
                # Flye uses. (Well, at the moment.)
                raise GraphParsingError(
                    f"{err_prefix} has a label containing more than one '\\l' "
                    "separator?"
                )

            # Get the edge ID
            id_part = parts[0]
            id_parts = id_part.split()
            # We already know that id_part should start with "id", but let's
            # go further here and verify that it starts with "id ". Is this ...
            # necessary? I dunno, but we may as well be thorough.
            if id_parts[0] != "id" or len(id_parts) != 2:
                raise GraphParsingError(
                    f"{err_prefix} has a label with a first line of "
                    f'"{id_part}". These lines should be formatted like '
                    '"id 500", for an edge with an ID of 500. Note that IDs '
                    "shouldn't contain any whitespace."
                )
            eid = id_parts[1]
            # Enforce the restriction that edge IDs must be unique. We don't
            # really need to do this (lots of graph filetypes don't even have
            # edge IDs), but... it's nice to know this. (And probably duplicate
            # IDs here would be a symptom of bugs or other problems upstream
            # that the user should look into.)
            if eid in seen_flye_edge_ids:
                raise GraphParsingError(
                    f"{err_prefix} has the ID {eid}, but other edge(s) in "
                    "this file have the same ID."
                )
            seen_flye_edge_ids.add(eid)

            # Get the length and coverage
            lencov_part = parts[1]
            lencov_parts = lencov_part.split()
            if len(lencov_parts) != 2:
                raise GraphParsingError(
                    f"{err_prefix} has a label where the second line is "
                    f'"{lencov_part}". This line should contain just the edge '
                    'length (e.g. "56k") and coverage (e.g. "80x"), separated '
                    "by a single space character."
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
                    elen = round(elen_thousands * 1000)
                else:
                    raise GraphParsingError(
                        f'{err_prefix} has a confusing length of "{elen_str}"?'
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
                        f"{err_prefix} has a confusing coverage of "
                        f'"{ecov_str}"?'
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
                    "edge(s) in the same file look like they came from Flye?"
                )
            # LJA can generate labels spanning multiple lines (although
            # jumboDBG's labels seem mostly to span single lines). The first
            # line of the label is what we mainly care about.
            label_first_line = label.splitlines()[0]
            lfl_match = re.match(LJA_LFL_PATT, label_first_line)
            if lfl_match is None:
                # we could make this error message more descriptive, but it
                # probably won't be encountered by most users so i don't think
                # it's super urgent
                raise GraphParsingError(
                    f"{err_prefix} looks like it came from LJA, but its label "
                    f'has an invalid first line of "{label_first_line}". LJA '
                    "labels should have a first line formatted like "
                    '"1234.56 A 99(2)" (corresponding to '
                    '"[ID] [first nt] [length]([coverage])").'
                )

            groups = lfl_match.groups()

            # The length and (K+1)-mer-cov lines could cause errors if these
            # aren't valid numbers. That's fine -- like in the Flye parser, let
            # the errors propagate up to the user.
            g.edges[e[:3]]["id"] = groups[0]
            g.edges[e[:3]]["first_nt"] = groups[1]
            g.edges[e[:3]]["length"] = int(groups[2])
            g.edges[e[:3]]["kp1mer_cov"] = float(groups[3])

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

            # If the label spans multiple lines, then it could be useful to
            # keep it around for the visualization. So, we will not delete
            # this label from the edge data. (Maybe we can change this in the
            # future if the space incurred by storing these labels becomes
            # prohibitively large.)
            lja_vibes = True

    if not seen_one_edge:
        # For "node-major" graphs I guess this is ok. For de Bruijn graphs,
        # though, we are going to have problems. Probably.
        raise GraphParsingError("DOT-format graph contains 0 edges.")

    # Only one of these should be True. ("^" is the XOR operator in Python.)
    # I thiiiink this case will only get triggered if, uh, there aren't any
    # edges in the graph (which already should have been taken care of above).
    # But I'm keeping this here just in case I messed something up.
    if not (lja_vibes ^ flye_vibes):
        raise WeirdError("Call a priest. Something went wrong.")

    # Both Flye and LJA DOT files, as of writing, provide some cosmetic
    # node-specific attributes which I don't think we need to care about here.
    #
    # Both Flye and LJA use "style" = "filled" for all nodes; Flye seems to
    # only a "fillcolor" of "grey", while LJA mostly seems to use a "fillcolor"
    # of "white". (Although it looks like it can sometimes assign a "fillcolor"
    # of "yellow" -- https://github.com/AntonBankevich/LJA/blob/acc02846ed10ae1b7fc49bc587b9adbee58d5a52/src/projects/dbg/visualization.hpp#L129
    # -- but I don't understand what causes this exactly, since it depends on
    # this function (https://github.com/AntonBankevich/LJA/blob/a066b5248fd42b7fd6e5259ef1dce6c6a229351a/src/projects/dbg/component.cpp#L155-L165).
    #
    # To limit confusion and save space, we delete these attributes here
    # (I can adjust this to pass these colors on to the visualization if
    # desired).
    for n in g.nodes:
        if "style" in g.nodes[n]:
            del g.nodes[n]["style"]
        if "fillcolor" in g.nodes[n]:
            del g.nodes[n]["fillcolor"]

    return g


# Lowercase filetype suffixes, which we'll use to figure out which parser we
# should use for a file.
#
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

FILETYPE2HR = {
    "lastgraph": "LastGraph",
    "gml": "GML",
    "gfa": "GFA",
    "fastg": "FASTG",
    "gv": "DOT",
    "dot": "DOT",
}

# Are the sequences stored on the nodes or the edges?
HRFILETYPE2NODECENTRIC = {
    "LastGraph": True,
    "GML": True,
    "GFA": True,
    "FASTG": True,
    "DOT": False,
}

# Are the sequence names include a prefix with their orientation?
HRFILETYPE2ORIENTATION_IN_NAME = {
    "LastGraph": True,
    "GML": False,
    "GFA": True,
    "FASTG": True,
    "DOT": True,
}


def sniff_filetype(filename):
    """Attempts to determine the filetype of the file specified by a filename.

    It might be worth extending this in the future to try sniffing via more
    sophisticated methods (i.e. actually checking the first few characters in
    these files), but this is an okay solution for now.

    Returns
    -------
    filetype: str
        The filename's extension.

    Raises
    ------
    NotImplementedError
        If the filename doesn't end with one of the supperted input filetype
        suffixes.
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
