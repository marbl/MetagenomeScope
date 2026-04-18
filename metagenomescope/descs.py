#!/usr/bin/env python3

GRAPH = "In GFA, FASTG, DOT, GML, or LastGraph format."

FASTA = (
    "FASTA file describing the sequences of the nodes (GFA, FASTG, GML, "
    "LastGraph) or edges (DOT)."
)

AGP = "AGP file describing paths."

VERKKO_PATH_TSV = "Verkko assembly.paths.tsv file describing paths."

FLYE_ASM_INFO = "Flye assembly_info.txt file describing contigs/scaffolds."

NODE_DATA = "CSV file describing node data, indexed by node ID."

EDGE_DATA = (
    "CSV file describing edge data, indexed by edge ID (Flye DOT) or "
    "by source and target columns (other graphs)."
)

TSV = "If given, assume -n/-e files use tabs (TSV) instead of commas (CSV)."

PORT = "Server port number."

VERBOSE = "Log extra details."

DEBUG = "Use Dash's debug mode."
