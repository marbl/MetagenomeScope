#!/usr/bin/env python3

GRAPH = "GFA, FASTG, DOT, GML, or LastGraph."

FASTA = (
    "FASTA file describing the sequences of the nodes (GFA, FASTG, GML, "
    "LastGraph) or edges (DOT)."
)

AGP = "AGP file describing paths of nodes."

OUTPUT_DIR = (
    "If provided, we'll save an interactive visualization of the graph to "
    "this directory. The directory will contain an index.html file; you can "
    "open this file in a web browser to access the visualization. If we "
    "cannot create this directory for some reason (e.g. it already exists), "
    "we'll raise an error."
)

OUTPUT_DOT = (
    "If provided, we'll save a DOT file describing the graph to this "
    "filepath. Identified patterns will be represented in this DOT file as "
    '"cluster" subgraphs.'
)

OUTPUT_CCSTATS = (
    "If provided, we'll save a tab-separated values (TSV) file describing the "
    "numbers of nodes, edges, and structural patterns in each connected "
    "component of the graph to this filepath."
)

ASSUME_ORIENTED = (
    "Assume that the nodes in a graph are already oriented, and doesn't "
    "create duplicates. This will only work with graphs where, for every "
    "node, its reverse complement node is not present in the same connected "
    "component; if this is the case for any node, then an error will be "
    "raised. THIS OPTION ISN'T FINISHED YET!"
)

NODE_METADATA = (
    "TSV file mapping some or all of the graph's node IDs (rows) to arbitrary "
    "metadata fields (columns)."
)

EDGE_METADATA = (
    "TSV file mapping some or all of the graph's edges (rows) to arbitrary "
    "metadata fields (columns). The leftmost two columns in this file should "
    "contain the source and sink node ID of the edge being described in a "
    "row; if there exist parallel edges in the graph between a given source "
    "and sink node, then that row's metadata will be applied to all such "
    "edges."
)

IMPACTS = "Impacts all output options (-o, -od, -os)."

PATTERNS_FLAG = (
    "If --patterns is set, we'll identify structural patterns (e.g. bubbles) "
    "in the graph; if --no-patterns is set, we won't identify any patterns. "
    f"{IMPACTS}"
)

# TODO: actually change way this works so that -ubl always true
MBF = (
    "File describing pre-identified bubbles in the graph, in the format "
    "of MetaCarvel's bubbles.txt output: each line of the file is formatted "
    "as (source label)(tab)(sink label)(tab)(all node labels in the bubble, "
    "including source and sink labels, all separated by tabs). Please see the "
    "MetaCarvel documentation at https://github.com/marbl/MetaCarvel for "
    "more details on MetaCarvel. This option can only be used if the input "
    "graph is a MetaCarvel GML file; otherwise, this will raise an error."
)

UP = (
    "File describing any pre-identified structural patterns in the graph: "
    "each line of the file should be formatted as "
    "(pattern type)(tab)(all node IDs in the pattern, all separated by tabs). "
    "If (pattern type) is 'Bubble' or 'Frayed Rope', then the pattern will be "
    "represented in the visualization as a Bubble or Frayed Rope, "
    "respectively; otherwise, the pattern will be represented as a generic "
    "'misc. user-specified pattern,' and colored accordingly in the "
    "visualization."
)

SPQR = (
    "Compute data for the SPQR 'decomposition modes' in the visualization. "
    "Necessitates a few additional system requirements; see MetagenomeScope's "
    "installation instructions wiki page for details."
)


PG = (
    "Save all .gv (DOT) files generated for nontrivial (i.e. containing > 1 "
    "node, or at least 1 edge or node group) connected components."
)

PX = "Save all .xdot files generated for nontrivial connected components."

NBDF = (
    'Saves .gv (DOT) files without cluster "backfilling" for each '
    "nontrivial connected component in the graph."
)

NPDF = (
    "Saves .gv (DOT) files without any structural pattern information "
    "embedded."
)
