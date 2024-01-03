# MetagenomeScope development documentation

Thanks for your interest in this project! Or, at least, I'm assuming you're
interested, because you clicked on this document, and you're reading it now,
and wow, you're still reading this sentence -- aren't you a persistent person?
Okay, you've made it to the third sentence of this document; if you've made it
this far, our fates are now intertwined. You're now officially a maintainer of
this project.

## Code structure

MetagenomeScope's code is composed of two main components:

### 1. Preprocessing script

MetagenomeScope's **preprocessing script** (contained in the
`metagenomescope/` directory of this repository) is a mostly-Python script that
takes as input an assembly graph file and produces a directory containing a
HTML visualization of the graph. Once installed, it can be run from the command
line using the `mgsc` command.

### 2. Viewer interface

MetagenomeScope's **viewer interface** (contained in the
`metagenomescope/support_files/` directory
of this repository) is a client-side web application that visualizes laid-out
assembly graphs using [Cytoscape.js](https://js.cytoscape.org/). This interface
includes various features for interacting with the graph and the
identified structural patterns within it.

You should be able to load visualizations created by MetagenomeScope
in most modern web browsers (mobile browsers probably will also work, although
using a desktop browser is recommended).

## That was the worst developer documentation I've read in my life

Sorry -- I'll try to add more stuff here later `._.`
