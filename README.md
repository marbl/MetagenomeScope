# MetagenomeScope
[![Build Status](https://travis-ci.org/marbl/MetagenomeScope.svg?branch=master)](https://travis-ci.org/marbl/MetagenomeScope) [![Code Coverage](https://codecov.io/gh/marbl/MetagenomeScope/branch/master/graph/badge.svg)](https://codecov.io/gh/marbl/MetagenomeScope)

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

MetagenomeScope also contains a bunch of other features intended to simplify
exploratory analysis of assembly graphs, including tools for scaffold
visualization, path finishing, and coloring nodes by biological metadata (e.g.
GC content). (As mentioned above, many of these features are not available in
the current version yet.)

## Quick usage

To install MetagenomeScope:
```bash
pip install git+https://github.com/marbl/MetagenomeScope.git
```

To visualize a graph:
```
mgsc -i [path to your assembly graph] -o [output directory name]
```

#### What types of assembly graphs can I use as input?

Currently, this supports
LastGraph ([Velvet](https://www.ebi.ac.uk/~zerbino/velvet/)),
[GFA](https://gfa-spec.github.io/GFA-spec/) (e.g.
[Flye/MetaFlye](https://github.com/fenderglass/Flye)),
GML ([MetaCarvel](https://github.com/marbl/MetaCarvel)),
and FASTG ([SPAdes](https://cab.spbu.ru/software/spades/)) files.

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

## More thorough documentation

Coming soon.

## Demos

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
