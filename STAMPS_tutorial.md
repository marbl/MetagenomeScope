# MetagenomeScope STAMPS Tutorial: August 6, 2018

(Inspired by [this SEPP/TIPP tutorial](https://github.com/MGNute/stamps-tutorial/blob/master/tutorial.md).)

## Introduction

This tutorial covers the process of using MetagenomeScope's "preprocessing
script" to generate a visualization file that can be loaded in
MetagenomeScope's viewer interface. These directions assume you have access to
the MBL cluster.

Note that you don't really have to follow this tutorial all the way through.
There's plenty of
sample graphs available on MetagenomeScope's demo for you to try out, so don't
worry if you run into lots of problems with these instructions!

If you can't run the commands to
generate a visualization file, you can just skip down to [the bottom
section of this tutorial](#actually-visualizing-the-assembly-graph) and download the pre-made `shakya.db` file.

## Getting ready to generate a MetagenomeScope visualization
First things first, you'll need to log on to the MBL clusters, same way as
always. See [here](https://github.com/mblstamps/stamps2018/wiki/Installation#connecting-to-the-mbl-servers) for instructions.

Once you've logged in to the cluster, you'll need to get Graphviz (the program we use to lay out graphs) ready. You can load it using

```bash
module load graphviz
```

Next up, you'll need to load the module for Python 2 so that we can use `pip2`.
Note that the version here apparently needs to be 2.7.9 -- for some reason,
just saying `module load python2` gave me a weird error. Technology is weird
sometimes!

```bash
module load python/2.7.9
```

Now everything's ready for us to install PyGraphviz, which is a Python library
that lets Python programs like MetagenomeScope communicate with Graphviz.
Run the following command to install PyGraphviz in your home directory:

```bash
pip2 install --user --install-option="--include-path=/bioware/graphviz/include/graphviz" --install-option="--library-path=/bioware/graphviz/lib/graphviz" pygraphviz
```

There's one last step before we can get this ready. You'll need to modify an
environment variable to point to the Graphviz library files, so that
PyGraphviz is able to find this information. (This solution c/o page 17 of the
[PyGraphviz manual](http://pygraphviz.github.io/documentation/latest/pygraphviz.pdf).)
The following command should work for this:

```bash
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/bioware/graphviz/lib"
```

Ok! Now we can finally generate a visualization!

## Generating an assembly graph visualization

MetagenomeScope supports a variety of input graph filetypes, including
output from Velvet, MetaCarvel, and SPAdes/MEGAHIT. Feel free to use any
assembly graph file you have available!

If you don't have one on hand, though,
we've provided a sample assembly graph file (`shakya_oriented.gml`) on the MBL
cluster that you can use. The sequencing data from which this assembly graph
was created comes from a 64-genome bacterial/archaeal metagenome, discussed in
[Shakya et al. 2013](https://www.ncbi.nlm.nih.gov/pubmed/23387867).
The resulting assembly was scaffolded using
[MetaCarvel](https://github.com/marbl/MetaCarvel).

The demo assembly graph file is located at
`/class/stamps-shared/MgSc/shakya_oriented.gml`.

We can generate a visualization of this file using the following command:

```bash
python2 /class/stamps-shared/MgSc/graph_collator/collate.py -i /class/stamps-shared/MgSc/shakya_oriented.gml -o shakya
```

This command will generate a file named `shakya.db` in your current working
directory. This file is actually a SQLite3 database file; you can visualize it
in MetagenomeScope's viewer interface, which is hosted online at
[mgsc.umiacs.io](https://mgsc.umiacs.io/).

## Optional: inspecting the assembly graph

One of the advantages of using a common filetype like SQLite3 databases is that
lots of systems have tools that can handle these sorts of files.
If you'd like, we can leverage this to mess around with this database file a bit! We can use SQLite3 to inspect it.

You can load the graph using:

```bash
sqlite3 shakya.db
```

This will open up an interactive prompt. You can run SQLite3 commands here to
learn more information about the database file for the assembly graph
that MetagenomeScope just generated.

First off, let's find out some basic structural information about the graph.
This is stored in the `assembly` table, which contains general information
about the entire assembly graph.

```sql
.headers on
SELECT node_count, edge_count, component_count FROM assembly;
```

From here, we can see that the graph contains 379 nodes, 229 edges, and
comprises 156 [connected components](https://en.wikipedia.org/wiki/Connected_component_(graph_theory)).

Next, let's dig some more into the length statistics of the graph's nodes.

```sql
SELECT total_length, n50 FROM assembly;
```

So the sum of the lengths of every node in the graph comes out to around 13
million base pairs (bp). And the graph has an [N50 statistic](https://en.wikipedia.org/wiki/N50,_L50,_and_related_statistics#N50) of 139,691 bp.

MetagenomeScope sorts the connected components in the assembly graph in
descending order by the number of nodes they have (so that component 1 is the
largest, component 2 is the second-largest, and so on).
Let's try figuring out how many of the 379 total nodes in the assembly graph are in
its first (and therefore largest) component.

```sql
SELECT node_count FROM components WHERE size_rank = 1;
```

It turns out that only 37 nodes are in this component. Since we know that this
is the largest component -- and since we also know that the graph contains 156
connected components -- we can infer that the graph probably consists of a lot of
relatively small connected components.

You can run some more commands if you'd like -- see
[here](http://www.sqlitetutorial.net/sqlite-select/) for a tutorial regarding the
"SELECT" statement, which all of the above SQLite3 commands used.

When you're done looking around using SQLite3, you can exit the interface
by pressing Ctrl-D.

## Actually visualizing the assembly graph

Ok, enough messing around! We can actually view the assembly graph now.

If you're familiar with accessing servers from the command-line, you can use
the `scp` program to download the `shakya.db` file from the MBL cluster to your
computer.
But it's easiest to just download this
[pre-made version](http://mgsc.umiacs.io/sample/shakya.db) hosted on the
MetagenomeScope website, if you don't want to mess around with `scp` right now.
You can just download the pre-made `shakya.db` file by clicking on the above
link or using the following command in your computer's command prompt:

```bash
wget http://mgsc.umiacs.io/sample/shakya.db
```

Either way, you can load MetagenomeScope's viewer interface at [mgsc.umiacs.io](https://mgsc.umiacs.io/).

Once you've opened the viewer interface, you can select a file to visualize
from your computer using the "Choose .db file" button. The "Demo .db" button
can be used to load demo files already available on this instance of
MetagenomeScope's viewer interface.

After loading a graph file into MetagenomeScope's viewer interface, a few controls become enabled:

- The "Assembly info" button
    - This button opens a dialog showing some of the information about this
    graph we got from SQLite3 earlier.
- The "Standard Mode" controls
    - These controls can be used to select and draw a connected component of the
    assembly graph.
    - Remember that MetagenomeScope sorts connected components of the graph in
    descending order by node count: so component 1 will contain the most nodes out
    of all the connected components in the graph. 

Anyway, select "Draw connected component" to draw a component of the graph!

Most of the controls in MetagenomeScope's viewer interface are hopefully
self-explanatory. Let me know if you have any questions; after the class moves
on from the command-line portion of this tutorial, we'll walk through the
individual controls in the viewer interface together.
