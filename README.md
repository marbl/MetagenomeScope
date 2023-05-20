# MetagenomeScope

[![MgSc Python CI](https://github.com/marbl/Metagenomescope/actions/workflows/python.yml/badge.svg)](https://github.com/marbl/MetagenomeScope/actions/workflows/python.yml)
[![MgSc JavaScript CI](https://github.com/marbl/Metagenomescope/actions/workflows/js.yml/badge.svg)](https://github.com/marbl/MetagenomeScope/actions/workflows/js.yml)
[![Code Coverage](https://codecov.io/gh/marbl/MetagenomeScope/branch/master/graph/badge.svg)](https://codecov.io/gh/marbl/MetagenomeScope)

![Screenshot of MetagenomeScope's standard mode, showing an example assembly graph from Nijkamp et al. 2013](https://user-images.githubusercontent.com/4177727/100696036-6aa7ab80-3347-11eb-8017-f693aae08aa2.png "Screenshot of MetagenomeScope showing an example assembly graph from Nijkamp et al. 2013.")
<div align="center">
(Assembly graph based on Fig. 2(a) in <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3916741/">Nijkamp et al. 2013</a>.)
</div>

## NOTE: MetagenomeScope is currently being refactored!
Some features that were previously in MetagenomeScope are not currently
re-implemented yet -- this should be changed soon. Thanks for bearing with me
as I work on improving this, and please let me know if you have any questions.

## Summary

MetagenomeScope is an interactive visualization tool designed for (meta)genomic
sequence assembly graphs. The tool aims to display a [hierarchical
layout](https://en.wikipedia.org/wiki/Layered_graph_drawing) of the input graph
while emphasizing the presence of small-scale details that can correspond to
interesting biological properties of the assembly.

Some of the features MetagenomeScope includes:

- Identifies and visually highlights "structural patterns" in the graph
  (bubbles, chains, cyclic chains, frayed ropes)
  - Repeats these identifications iteratively in order to support the
    decomposition of complex regions of the graph
  - Allows users to interactively collapse or uncollapse these patterns, in
    order to display the graph at different levels of detail

- Uses [Graphviz](https://www.graphviz.org/)'
  [`dot`](https://www.graphviz.org/pdf/dotguide.pdf) tool to hierarchically
  lay out each connected component of the graph

- Given an [AGP file](https://www.ncbi.nlm.nih.gov/assembly/agp/AGP_Specification/)
   describing, for example, scaffolds consisting of multiple contigs, supports
   visualization of these as paths through the graph

- Interactive path finishing

- Coloring nodes and edges by arbitrary metadata (e.g. GC content, coverage)

(As mentioned above, many of these features are not available in
the current version yet.)

## Installation

Probably the easiest way to install MetagenomeScope is using a
[conda](https://docs.conda.io/en/latest/) environment. Eventually we'll put
this up on bioconda or something, but until then you can use the following
steps:

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

### Troubleshooting your installation

Getting Graphviz and PyGraphviz installed -- and getting them to communicate
with each other -- can be tricky. I'm looking into ways of making this less
painful; for now, if you run into problems, please feel free to [contact
me](#contact) and I'll try to help out.

## Documentation

### Visualizing an assembly graph

Assuming you've activated the conda environment we just created,
visualizing an assembly graph can be done in one command:

```
mgsc -i [path to your assembly graph] -o [output directory name]
```

The output directory will contain an `index.html` file that can be opened in
most modern web browsers. (The `index.html` file points to other resources
located within the directory, so please don't move it out of the directory.)

### What types of assembly graphs can this tool visualize?

Currently, MetagenomeScope supports the following filetypes:

<!-- TODO: I haven't tested miniasm, hifiasm(-meta), and MEGAHIT output graphs here;
should do that to verify that their graphs work ok -->

| Filetype | Tools that output this filetype | Notes |
| -------- | ------------------------------- | ----- |
| [GFA](https://gfa-spec.github.io/GFA-spec/) (`.gfa`) | [(meta)Flye](https://github.com/fenderglass/Flye), [LJA](https://github.com/AntonBankevich/LJA), [miniasm](https://github.com/lh3/miniasm), [hifiasm](https://github.com/chhylp123/hifiasm), [hifiasm-meta](https://github.com/xfengnefx/hifiasm-meta), ... | Both GFA v1 and GFA v2 files are accepted, but [currently](https://github.com/marbl/MetagenomeScope/issues/147) only the raw structure (segments and links) are included. |
| FASTG (`.fastg`) | [SPAdes](https://cab.spbu.ru/software/spades/), [MEGAHIT](https://github.com/voutcn/megahit) | Expects SPAdes-"dialect" FASTG files: see [pyfastg's documentation](https://github.com/fedarko/pyfastg) for details. |
| [DOT](https://en.wikipedia.org/wiki/DOT_(graph_description_language)) (`.dot`, `.gv`) | [(meta)Flye](https://github.com/fenderglass/Flye), [LJA](https://github.com/AntonBankevich/LJA) | Expects DOT files produced by Flye or LJA. Visualizing DOT files (rather than the GFA files also produced by these assemblers) can be preferable because GFA and FASTG files [are not ideal](https://github.com/AntonBankevich/LJA/blob/main/docs/jumbodbg_manual.md#output-of-de-bruijn-graph-construction) for representing graphs in which sequences are stored on edges rather than nodes (e.g. de Bruijn graphs); the DOT files output by Flye and LJA should contain the _original_ structure of these graphs (in which edges and nodes in the visualization actually correspond to edges and nodes in the original graph, respectively). |
| [GML](https://networkx.org/documentation/stable/reference/readwrite/gml.html) (`.gml`) | [MetaCarvel](https://github.com/marbl/MetaCarvel) | Expects MetaCarvel-"dialect" GML files. |
| [LastGraph](https://github.com/dzerbino/velvet/blob/master/Manual.pdf) (`.LastGraph`) | [Velvet](https://github.com/dzerbino/velvet) | Only the raw structure (nodes and arcs) are included. |

If you run into any additional assembly graph filetypes you'd like us to
support ([...and/or if any more of these filetypes get created in the next few years](https://xkcd.com/927/)), please [let us know](#contact)!

### Vignettes

<details>
  <summary><strong>I just want to visualize an assembly graph.</strong></summary>

Let's say the assembly graph is located in a file named `graph.gfa`. We can use
the following command:

```
mgsc -i graph.gfa -o viz
```

This will create a visualization of this assembly graph in the directory
`viz/`.
</details>

<details>
  <summary><strong>I want to visualize an assembly graph, but I don't care
about the "pattern identification" stuff. Can you just show me the raw
structure of the graph?</strong></summary>

Sure! The `--no-patterns` flag will disable pattern identification.

```
mgsc -i graph.gfa -o vizraw --no-patterns
```
This will create a visualization of this assembly graph, without any patterns
identified, in the directory `vizraw/`.
</details>

<details>
  <summary><strong>I've got a really big graph, and I don't want to visualize
it -- I just want to get a summary of how many nodes, edges, bubbles, etc. are
present in each component of the graph.</strong></summary>

The `-os` / `--output-ccstats` option will write out a
[TSV file](https://en.wikipedia.org/wiki/Tab-separated_values)
describing the numbers of nodes, edges, and each type of identified pattern in
all components in the assembly graph.

This option is a simple way to summarize even massive graphs; it can be useful
if you're working, for example, on a remote server (and you just want an
overview of the basic structure of a graph's components).

If your graph is large enough, and if you don't intend to visualize it anyway,
then you will probably also want to disable the `-maxn` and `-maxe` options
(and thus tell MetagenomeScope to consider all components, no matter how large
they are).

The following command produces a TSV file named `stats.tsv` summarizing all
components (no matter how large) of an assembly graph:

```
mgsc -i graph.gfa -os stats.tsv -maxn 0 -maxe 0
```
</details>

### FAQs

(The title "FAQ" is kind of a lie because I don't think anyone has asked me any
of these questions yet. Maybe we can just act like the "F" in "FAQ" stands for
"future"?)

<!-- use of <strong> here was stolen from strainflye's readme, which in turn is
based on https://codedragontech.com/createwithcodedragon/how-to-style-html-details-and-summary-tags/ -->
<details>
  <summary><strong>What's the deal with "reverse complement" nodes/edges?</strong></summary>

#### "Explicit" graph filetypes (FASTG, DOT, GML)

To make a long story short: when MetagenomeScope reads in FASTG, DOT, and GML files,
it assumes that _these files explicitly describe all of the nodes and edges in the graph_.
So, let's say you give MetagenomeScope the following DOT file:

```dot
digraph g {
  1 -> 2 [label="A99(2.4)"];
}
```

We will interpret this as a graph with **two nodes** (`1`, `2`) and **one edge**
(`1 -> 2`).

#### "Implicit" graph filetypes (GFA, LastGraph)

However, for GFA and LastGraph files, MetagenomeScope cannot make the
assumption that these files explicitly describe all of the nodes and edges in
the graph: in these files, each declaration of a node / edge
(in GFA parlance, "segment" / "link"; in LastGraph parlance, "node"
/ "arc") also declares this node / edge's reverse complement.
So, let's say you give MetagenomeScope the following GFA file (based on
[this example](https://github.com/sjackman/gfalint/blob/master/examples/sample1.gfa)):

```gfa
H	VN:Z:1.0
S	1	CGATGCAA
S	2	TGCAAAGTAC
L	1	+	2	+	5M
```

We will interpret this as a graph with **four nodes** (`1`, `-1`, `2`, `-2`)
and **two edges** (`1 -> 2`, `-2 -> -1`). The presence of node `X`
["implies"](https://github.com/bcgsc/abyss/wiki/ABySS-File-Formats#reverse-complement)
the existence of the reverse complement node `-X`, and the presence of edge
`X -> Y` "implies" the existence of the reverse complement edge `-Y -> -X`.
This is analogous to [how "double mode" works in Bandage](https://github.com/rrwick/Bandage/wiki/Single-vs-double-node-style).

#### Impacts of reverse complement nodes / edges on the graph structure

Often, the presence of reverse complement nodes / edges (whether
they are explicitly described in a FASTG, DOT, or GML file, or are implicitly
described in a GFA or LastGraph file) doesn't impact the graph structure much.

What does this mean? Consider the GFA example above. There are four nodes and
two edges in this graph, but they form two
[(weakly) connected components](https://en.wikipedia.org/wiki/Component_(graph_theory)) --
that is, the graph contains one "island" of `1` and `2` (which are connected to
each other), and another "island" of `-1` and `-2` (which are also connected to each other).
You can think of these entire components as "reverse complements" of each other:
although MetagenomeScope will visualize both of them
([at least right now](https://github.com/marbl/MetagenomeScope/issues/67)),
you don't really need to analyze them separately. They describe the same
sequences, just in different directions.\*

_This is not always the case_, though. Sometimes a node and its reverse
complement may wind up in the same component, for example in the following GFA
file (which contains an extra "link" line relative to the GFA file we
considered above):

```gfa
H	VN:Z:1.0
S	1	CGATGCAA
S	2	TGCAAAGTAC
L	1	+	2	+	5M
L	1	+	2	-	2D1M
```

This graph (still containing **four nodes** [`1`, `-1`, `2`, `-2`], but now
containing **four edges** [`1 -> 2`, `-2 -> -1`, `1 -> -2`, `2 -> -1`]) takes up only a single
weakly connected component.

\* The statement that reverse complements "describe the same sequences, just in
different directions" is technically not true for LastGraph files. Consider a node `N` in a
LastGraph file: the sequence represented by `N` will not be exactly equal to the reverse
complement of the sequence represented by `-N`, since these sequences are slightly
shifted. See
[the Bandage wiki](https://github.com/rrwick/Bandage/wiki/Assembler-differences#velvet)
for a nice figure and explanation. (That being said, the intuition for
"thinking about reverse complement nodes / edges" here is pretty much the same
as it is for other files.)

#### Based on the FASTG specification, shouldn't FASTG be an "implicit" instead of an "explicit" filetype?

It's complicated. The way I interpret the FASTG specification, each declaration
of an edge sequence implicitly also declares this edge sequence's reverse complement; however,
this is not the case for "adjacencies" between edge sequences.

In any case, the "dialect" of FASTG files produced by SPAdes and MEGAHIT lists edge sequences
and their reverse complements (as well as adjacencies between edge sequences and their reverse complements)
separately. Because of this, we consider FASTG to be an "explicit" filetype.
(See [pyfastg's documentation](https://github.com/fedarko/pyfastg#about-reverse-complements)
for details on how we handle reverse complements in FASTG files.)
</details>

<details>
  <summary><strong>What happens if an edge is its own reverse complement?</strong></summary>

You really like asking hard questions, don't you? ;)

This can happen if an edge exists from `X -> -X` or from `-X -> X` in an
"implicit" graph file (GFA / LastGraph). Consider
[this GFA file](https://github.com/sjackman/assembly-graph/blob/master/loop.gfa),
c/o Shaun Jackman:

```gfa
H	VN:Z:1.0
S	1	AAA
S	2	ACG
S	3	CAT
S	4	TTT
L	1	+	1	+	2M
L	2	+	2	-	2M
L	3	-	3	+	2M
L	4	-	4	-	2M
```

Since this GFA file contains four "link" lines, we might think at first that the corresponding graph
contains 4 × 2 = 8 edges. However, the graph only contains **6 unique
edges**. This is because the reverse complement of `2 -> -2` is itself:
we know from above that `X -> Y` implies `-Y -> -X`, but
`-(-2) -> -(2)` is equal to `2 -> -2`! The same goes for `-3 -> 3`:
`-(3) -> -(-3)` is equal to `-3 -> 3`.
Both of these edges "imply" themselves as their own reverse complements!

How do we handle this situation? As of writing,
when MetagenomeScope visualizes these graphs it will only draw one copy
of these "self-implying" edges. This matches
[the original visualization of this graph](https://github.com/sjackman/assembly-graph/blob/master/loop.gv.png), and also matches Bandage's visualization of this GFA file.

Notably, since we assume that "explicit" graph files (FASTG / DOT / GML)
explicitly define all of the nodes and edges in their graph, MetagenomeScope doesn't do anything
special for this case for these files. (If your DOT file describes one edge
from `X -> -X`, then that's fine; if it describes two or more edges from `X -> -X`,
then that's also fine.)
</details>

<details>
  <summary><strong>Can my graphs have parallel edges?</strong></summary>

Yes! MetagenomeScope now supports
[multigraphs](https://en.wikipedia.org/wiki/Multigraph). If your assembly graph
file describes more than one edge from `X -> Y`, then MetagenomeScope will
visualize all of these "parallel" edges. (This situation often occurs when
visualizing de Bruijn graphs stored in DOT files.)

Notably, this is only supported right now for some filetypes. The
parsers MetagenomeScope uses for GFA and FASTG files
[do not allow multigraphs](https://github.com/marbl/MetagenomeScope/issues/239) -- this
means that, at the moment, trying to use MetagenomeScope to visualize a GFA or
FASTG file containing parallel edges will cause an error. I hope to address
this (at least for GFA files) soon.
</details>

<details>
  <summary><strong>What's the deal with the <code>-maxn</code> / <code>-maxe</code> options?</strong></summary>

By default, MetagenomeScope will apply these options to ignore large connected
components of the graph -- this is because performing hierarchical layout of
very large components can be computationally intensive.

You can turn off these settings (and
thus tell MetagenomeScope to look at _all_ components of the graph) by setting
both `-maxn` and `-maxe` to `0`.

</details>

### Full command-line usage

```
Usage: mgsc [OPTIONS]

  Visualizes and/or summarizes an assembly graph.

  MetagenomeScope supports multiple types of output (-o, -od, -os); you will
  probably want to start with -o.

  Please check out https://github.com/marbl/MetagenomeScope if you have any
  questions, suggestions, etc. about this tool.

Options:
  -i, --input-file FILE           Assembly graph file. We accept GFA, FASTG,
                                  DOT, GML, and LastGraph files.  [required]
  -o, --output-viz-dir PATH       If provided, we'll save an interactive
                                  visualization of the graph to this
                                  directory. The directory will contain an
                                  index.html file; you can open this file in a
                                  web browser to access the visualization. If
                                  we cannot create this directory for some
                                  reason (e.g. it already exists), we'll raise
                                  an error.
  -od, --output-dot FILE          If provided, we'll save a DOT file
                                  describing the graph to this filepath.
                                  Identified patterns will be represented in
                                  this DOT file as "cluster" subgraphs.
  -os, --output-ccstats FILE      If provided, we'll save a tab-separated
                                  values (TSV) file describing the numbers of
                                  nodes, edges, and structural patterns in
                                  each connected component of the graph to
                                  this filepath.
  -n, --node-metadata FILE        TSV file mapping some or all of the graph's
                                  node IDs (rows) to arbitrary metadata fields
                                  (columns).
  -e, --edge-metadata FILE        TSV file mapping some or all of the graph's
                                  edges (rows) to arbitrary metadata fields
                                  (columns). The leftmost two columns in this
                                  file should contain the source and sink node
                                  ID of the edge being described in a row; if
                                  there exist parallel edges in the graph
                                  between a given source and sink node, then
                                  that row's metadata will be applied to all
                                  such edges.
  -maxn, --max-node-count INTEGER RANGE
                                  We will not consider connected components
                                  containing more than this many nodes. This
                                  option is provided because hierarchical
                                  graph layout is relatively slow for large /
                                  tangled components, and because the
                                  interactive visualization can be slow for
                                  large graphs. Impacts all output options
                                  (-o, -od, -os). Setting this to 0 removes
                                  this limit.  [default: 7999; x>=0]
  -maxe, --max-edge-count INTEGER RANGE
                                  We will not visualize connected components
                                  containing more than this many edges.
                                  Impacts all output options (-o, -od, -os).
                                  Setting this to 0 removes this limit.
                                  [default: 7999; x>=0]
  --patterns / --no-patterns      If --patterns is set, we'll identify
                                  structural patterns (e.g. bubbles) in the
                                  graph; if --no-patterns is set, we won't
                                  identify any patterns. Impacts all output
                                  options (-o, -od, -os).  [default: patterns]
  -v, --version                   Show the version and exit.
  -h, --help                      Show this message and exit.
```

## Demo visualizations

Some early demos are available online. We'll probably add more of these in the
future.

- [Marygold Fig. 2(a) graph](https://marbl.github.io/MetagenomeScope/demos/marygold/index.html)
  - See [Nijkamp et al. 2013](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3916741/) for details.
    This graph was based on the topology shown in Fig. 2(a) of this paper.

- [Velvet E. coli graph](https://marbl.github.io/MetagenomeScope/demos/bandage-ecoli-example/index.html)
  - This graph is example data from the website of [Bandage](http://rrwick.github.io/Bandage/)
    (which is another great tool for visualizing assembly graphs :)

## License

MetagenomeScope is licensed under the
[GNU GPL, version 3](https://www.gnu.org/copyleft/gpl.html).

License information for MetagenomeScope's dependencies is included in the root directory of this repository, in `DEPENDENCY_LICENSES.txt`. License copies for dependencies distributed/linked with MetagenomeScope -- when not included with their corresponding source code -- are available in the `dependency_licenses/` directory.

## Acknowledgements

See the [acknowledgements page](https://github.com/marbl/MetagenomeScope/wiki/Acknowledgements) on the wiki for a list of acknowledgements
for MetagenomeScope's codebase.

## Contact

MetagenomeScope was created by members of the [Pop Lab](https://sites.google.com/a/cs.umd.edu/poplab/) in the [Center for Bioinformatics and Computational Biology](https://cbcb.umd.edu/) at the [University of Maryland, College Park](https://umd.edu/).

Feel free to email `mfedarko (at) ucsd (dot) edu` with any questions, suggestions, comments, concerns, etc. regarding the tool. You can also [open an issue](https://github.com/marbl/MetagenomeScope/issues) in this repository, if you'd like.
