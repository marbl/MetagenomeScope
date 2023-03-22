# MetagenomeScope

[![MgSc Python CI](https://github.com/marbl/Metagenomescope/actions/workflows/python.yml/badge.svg)](https://github.com/marbl/MetagenomeScope/actions/workflows/python.yml)
[![MgSc JavaScript CI](https://github.com/marbl/Metagenomescope/actions/workflows/js.yml/badge.svg)](https://github.com/marbl/MetagenomeScope/actions/workflows/js.yml)
[![Code Coverage](https://codecov.io/gh/marbl/MetagenomeScope/branch/master/graph/badge.svg)](https://codecov.io/gh/marbl/MetagenomeScope)

![Screenshot of MetagenomeScope's standard mode, showing an example assembly graph from Nijkamp et al. 2013](https://user-images.githubusercontent.com/4177727/100696036-6aa7ab80-3347-11eb-8017-f693aae08aa2.png "Screenshot of MetagenomeScope showing an example assembly graph from Nijkamp et al. 2013.")
<div align="center">
(Assembly graph based on Fig. 2(a) in Nijkamp et al. 2013.)
</div>

## NOTE: MetagenomeScope is currently being refactored!
Some features that were previously in MetagenomeScope are not currently
re-implemented yet -- this should be changed soon. Thanks for bearing with me
as I work on improving this, and please let me know if you have any questions.

## Summary

MetagenomeScope is an interactive visualization tool designed for metagenomic
sequence assembly graphs. The tool aims to display a [hierarchical
layout](https://en.wikipedia.org/wiki/Layered_graph_drawing) of the input graph
while emphasizing the presence of small-scale details that can correspond to
interesting biological features in the data.

To this end, MetagenomeScope
highlights certain "structural patterns" of contigs in the graph (repeating the
pattern identification hierarchically),
splits the graph into its connected components (by default only displaying one
connected component at a time),
and uses [Graphviz](https://www.graphviz.org/)'
[`dot`](https://www.graphviz.org/pdf/dotguide.pdf) tool to hierarchically
lay out each connected component of the graph.

MetagenomeScope also contains many other features intended to simplify
exploratory analysis of assembly graphs, including tools for scaffold
visualization, path finishing, and coloring nodes by biological metadata (e.g.
GC content). (As mentioned above, many of these features are not available in
the current version yet.)

## Quick installation and usage

Probably the easiest way to install MetagenomeScope is using a
[conda](https://docs.conda.io/en/latest/) environment:

```bash
# Download the YAML file describing the conda packages we'll install
wget https://raw.githubusercontent.com/marbl/MetagenomeScope/main/environment.yml

# Create a new conda environment based on this YAML file
# (by default, it'll be named "mgsc")
conda env create -f environment.yml

# Activate this conda environment
conda activate mgsc

# Install the actual MetagenomeScope software
pip install git+https://github.com/marbl/MetagenomeScope.git
```

Assuming you are currently in the conda environment we just created,
visualizing an assembly graph can be done in one command:

```
mgsc -i [path to your assembly graph] -o [output directory name]
```

The output directory will contain an `index.html` file that can be opened in
most modern web browsers. (The file points to other resources within the
directory, so please don't move it out of the directory.)

#### What types of assembly graphs can I use as input?

Currently, MetagenomeScope supports the following filetypes:

<!-- TODO: I haven't tested miniasm and hifiasm(-meta) output graphs here --
should do that to verify that their graphs work ok -->

| Filetype | Assemblers that output this filetype | Notes |
| -------- | ------------------------------------ | ----- |
| [GFA](https://gfa-spec.github.io/GFA-spec/) (`.gfa`) | [(meta)Flye](https://github.com/fenderglass/Flye), [LJA](https://github.com/AntonBankevich/LJA), [miniasm](https://github.com/lh3/miniasm), [hifiasm](https://github.com/chhylp123/hifiasm), [hifiasm-meta](https://github.com/xfengnefx/hifiasm-meta), ... | Both GFA v1 and GFA v2 files are accepted, but [currently](https://github.com/marbl/MetagenomeScope/issues/147) only the raw structure (segments and links) are included. |
| [DOT](https://en.wikipedia.org/wiki/DOT_(graph_description_language)) (`.dot`, `.gv`) | [(meta)Flye](https://github.com/fenderglass/Flye), [LJA](https://github.com/AntonBankevich/LJA) | GFA and FASTG files [are not ideal for storing de Bruijn graphs](https://github.com/AntonBankevich/LJA/blob/main/docs/jumbodbg_manual.md#output-of-de-bruijn-graph-construction) or other graphs in which sequences are stored on edges rather than nodes. To visualize the _original_ structure of these graphs (in which edges in the visualization actually correspond to edges in the original graph), you can provide the DOT file rather than the GFA file. |
| FASTG (`.fastg`) | [SPAdes](https://cab.spbu.ru/software/spades/) | Expects SPAdes-"dialect" FASTG files: see [pyfastg's documentation](https://github.com/fedarko/pyfastg) for details. |
| [GML](https://networkx.org/documentation/stable/reference/readwrite/gml.html) (`.gml`) | [MetaCarvel](https://github.com/marbl/MetaCarvel) | Expects MetaCarvel-"dialect" GML files |
| LastGraph (`.LastGraph`) | [Velvet](https://github.com/dzerbino/velvet) | Only the raw structure (nodes and arcs) are included. |

## Code structure

MetagenomeScope is composed of two main components:

### 1. Preprocessing script

MetagenomeScope's **preprocessing script** (contained in the
`metagenomescope/` directory of this repository) is a mostly-Python script that
takes as input an assembly graph file and produces a directory containing a
HTML visualization of the graph. Once installed, it can be run from the command
line using the `mgsc` command.

**Note.** By default, connected components containing 8,000 or more nodes or
edges will not be laid out. These thresholds are configurable using the
`--max-node-count` / `--max-edge-count` parameters. This default is intended
to save time and effort: hierarchical layout can take a really long time for
complex and/or large connected components, so oftentimes trying to visualize
the largest few components of a graph will take an intractable amount of
computational resources / time. Furthermore, really complex components of
assembly graphs can be hard to visualize meaningfully.

This isn't always the case (for example, a
connected component containing 10,000 nodes all in a straight line will be
much easier to lay out and visualize than a connected component
with 5,000 nodes and 20,000 edges), but we wanted to be conservative with the
defaults.

### 2. Viewer interface

MetagenomeScope's **viewer interface** (contained in the
`metagenomescope/support_files/` directory
of this repository) is a client-side web application that visualizes laid-out
assembly graphs using [Cytoscape.js](https://js.cytoscape.org/).

This interface includes various features for interacting with the graph and the
identified structural patterns within it.

You should be able to load visualizations created by MetagenomeScope
in most modern web browsers (mobile browsers probably will also work, although
using a desktop browser is recommended).

## Installation notes

Getting Graphviz and PyGraphviz installed -- and getting them to communicate
with each other -- can be tricky. I'm looking into ways of making this less
painful; for now, if you run into problems, please feel free to contact me and
I'll try to help out.

## Demos

Some early demos are available online. We'll probably add more of these in the
future.

- [Marygold Fig. 2(a) graph](https://marbl.github.io/MetagenomeScope/demos/marygold/index.html)
  - See [Nijkamp et al. 2013](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3916741/) for details.
    This graph was based on the topology shown in Fig. 2(a) of this paper.

- [Velvet E. coli graph](https://marbl.github.io/MetagenomeScope/demos/bandage-ecoli-example/index.html)
  - This graph is example data from the website of [Bandage](http://rrwick.github.io/Bandage/)
    (which is another great tool for visualizing assembly graphs :)

## More thorough documentation

Coming soon.

## License

MetagenomeScope is licensed under the
[GNU GPL, version 3](https://www.gnu.org/copyleft/gpl.html).

License information for MetagenomeScope's dependencies is included in the root directory of this repository, in `DEPENDENCY_LICENSES.txt`. License copies for dependencies distributed/linked with MetagenomeScope -- when not included with their corresponding source code -- are available in the `dependency_licenses/` directory.

## Acknowledgements

See the [acknowledgements page](https://github.com/marbl/MetagenomeScope/wiki/Acknowledgements) on the wiki for a list of acknowledgements
for MetagenomeScope's codebase.

## Contact

MetagenomeScope was created by members of the [Pop Lab](https://sites.google.com/a/cs.umd.edu/poplab/) in the [Center for Bioinformatics and Computational Biology](https://cbcb.umd.edu/) at the [University of Maryland, College Park](https://umd.edu/).

Feel free to email `mfedarko (at) ucsd (dot) edu` with any questions, suggestions, comments, concerns, etc. regarding the tool. You can also open an [issue](https://github.com/marbl/MetagenomeScope/issues) in this repository, if you'd like.
