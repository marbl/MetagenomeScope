# Changelog

All notable changes to this project will be documented in this file.

As inspired by [Pyrodigal](https://github.com/althonos/pyrodigal),
this format is adapted from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
[Unreleased]: https://github.com/marbl/MetagenomeScope/compare/v1.3.0...HEAD

### Added

- Add a new section, "Style," in the drawing options dialog.

  - Currently, this contains controls that can be used to change how selected
    nodes are represented, and how wide various types of edges should be.

### Changed

- Dramatically speed up pattern decomposition, mostly by addressing a
  bottleneck in the bipartite-finding code
  ([#431](https://github.com/marbl/MetagenomeScope/issues/431),
  [#433](https://github.com/marbl/MetagenomeScope/issues/433)).

- Adjust default edge widths, and vary these defaults based on whether or not
  the input graph is node-centric or not. (Node-centric graphs get thicker
  edges by default.)

- By default, selecting a node now darkens it (and changes its label font
  from black to light gray) instead of giving it a border.
  You can choose to use borders instead of (or in addition to!) this behavior
  by using the new "Style" section controls.

- Various improvements to the README.


## [v1.3.0] - 2026-05-15 - GFA handling improvements, better component tiling, various CLI options
[v1.3.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v1.3.0

### Added

- Add the `-t`/`--vtsv` command-line option, to support reading
  [Verkko](https://github.com/marbl/verkko)-style TSV files describing paths
  ([#336](https://github.com/marbl/MetagenomeScope/issues/336)).

- Add the `--rmdup` command-line option, which controls whether or not to
  remove parallel edges.

  - _By default_, we do not do anything unless the graph is in GFA format.
    If the graph _is_ in GFA format, then MetagenomeScope will now remove
    parallel edges. This behavior can be adjusted using `--rmdup`.

  - See [#430](https://github.com/marbl/MetagenomeScope/issues/430) for some
    context.

- Add the `--decomp` command-line flag, which controls whether or not to run
  pattern decomposition
  ([#425](https://github.com/marbl/MetagenomeScope/issues/425)).

  - Turning decomposition off will just make MetagenomeScope behave as if it
    did not detect any patterns in your graph. This can be useful if you just
    want to interact with the raw graph structure (whether programmatically
    or in the interactive visualization), without having to think about the
    split nodes and fake edges caused by the decomposition.

  - _By default,_ this is set to `--decomp`: that is, decomposition is turned
    on.

- Add the `--dcheck` command-line flag, which controls whether or not to run
  a sanity check after pattern decomposition that verifies the integrity of
  the graph ([#421](https://github.com/marbl/MetagenomeScope/issues/421)).

  - This check involves, among other things, creating an extra copy of the
    input graph structure before decomposition. It can be a bottleneck when
    working with massive graphs on low-memory systems.

  - _By default,_ this is set to `--no-dcheck`: that is, this sanity check is
    turned off.

### Changed

- Implement a custom GFA parser. This dramatically speeds up loading large
  GFA files, and makes it easier to quietly ignore nonstandard GFA tags
  ([#310](https://github.com/marbl/MetagenomeScope/issues/310),
  [#403](https://github.com/marbl/MetagenomeScope/issues/403)).

- Explicitly ignore all GFA 2 edges that are not
  "[dovetails](https://gfa-spec.github.io/GFA-spec/GFA2.html#edge)."

  - Previously, we ignored containments, but still visualized "general edges"
    that were not dovetails. Now, to simplify things and keep interpretation
    straightforward, we ignore general edges as well.

  - Note that our rules for classifying dovetail edges are currently somewhat
    stricter than those outlined in the GFA 2 specification. See
    [this issue](https://github.com/GFA-spec/GFA-spec/issues/133) for details.

- Document (in the README FAQs) and formalize how we handle GFA 2 paths
  containing edges and other paths.

  - Previously, we were using Gfapy's [`captured_segments`](https://gfapy.readthedocs.io/en/latest/tutorial/references.html#induced-set-and-captured-path)
    property to do this for us. I am not 100% sure that the way we handle
    edges in these paths will always match Gfapy's, but it should be fine.

- By default, MetagenomeScope will now remove parallel edges in GFA files.
  As discussed in "Added" above, this can be controlled by `--rmdup`.

- Allow paths to span multiple connected components of the graph, since this
  can occur in Verkko output.

  - If a path spans multiple components, its `CC #` entry in the table of
    available paths will be a comma-separated list of these components (rather
    than just a single number). To account for this, the "type" of this column
    has been changed from `number` to `text` -- this will mean that sorting
    the paths table by this column will result in a different ordering.

- Previously, we would create an extra copy of each path in a GFA file
  representing the reverse-complementary copy of this path. Now, to be
  consistent with other path filetypes and make interpretation easier, we
  no longer do this
  ([#357](https://github.com/marbl/MetagenomeScope/issues/357)).

- Use a small amount of padding when fitting the graph drawing. This should
  make it easier to notice small parts of the graph that were previously right
  next to the border of the screen.

- Prevent node or edge IDs from beginning with `[N`. This makes parsing Verkko
  TSV files easier: with this restriction, we can now unambiguously say if
  something on a path is a gap or not.

- Add more detail to the `--verbose` log messages during pattern decomposition.

- Turn off the creation of `AssemblyGraph.original_graph`, the call to
  `AssemblyGraph._sanity_check_graph()`, etc. by default; as discussed in
  "Added" above, this is now controlled by the `--dcheck` command-line flag
  ([#421](https://github.com/marbl/MetagenomeScope/issues/421)).

- Clean up and add some more tests for the path-parsing parts of the code.

- Add some more tests for the GFA-parsing parts of the code.

- Removed some ancient test data / code that was previously in
  `metagenomescope/tests/input/extras/`.

- Cleaned up the test data descriptions in `metagenomescope/tests/input/README.md`.

- Various updates to the README.

### Fixed

- Improve connected component tiling, including fixing minor bugs in how we set
  total row widths and in how we labelled rows internally
  ([#358](https://github.com/marbl/MetagenomeScope/issues/358)).

  - Inspired by [Bandage](https://github.com/rrwick/Bandage/blob/f94d409a76bf6a13eef6af0a88476eaeffa71b32/ogdf/energybased/MAARPacking.cpp#L60),
    we now try to adjust the vertical padding between rows of components in
    order to fit a desired aspect ratio.

  - These changes should be particularly useful for graphs consisting of many
    long linear components.

- Fix a bug where Flye DOT files with split nodes / fake edges remaining
  after the decomposition would crash the redundant component detection
  ([commit `2a87720`](https://github.com/marbl/MetagenomeScope/commit/2a877209c9cfc90755ef4474f47add8b6e387f1b)).


## [v1.2.0] - 2026-03-27 - Nonredundant drawing, bug fixes, and cleaning up
[v1.2.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v1.2.0

### Added

- Add a new drawing method, `Entire graph (nonredundant)`, that draws the
  entire graph _but_ draws perfectly reverse-complementary components
  only once ([#67](https://github.com/marbl/MetagenomeScope/issues/67)).

- Add bioconda installation instructions to the README
  ([#302](https://github.com/marbl/MetagenomeScope/issues/302)).

- Add a brief note in the "drawing options" dialog that the client-side layout
  algorithms (dagre and fCoSE) may be impractical for large graphs.

- Add various tests (including many for the layout process).

- Add this Changelog.

### Changed

- For Flye DOT files, adjust the random color assignment so that edges `E` and
  `-E` are guaranteed to be assigned the same random color
  ([#401](https://github.com/marbl/MetagenomeScope/issues/401)).

- The icons used to represent layout algorithms in the "drawing options" dialog
  are now drawn with slightly thicker strokes. Um, in case that is relevant to
  you. Probably not.

- Clean up the internal formatting of edge control points
  ([#396](https://github.com/marbl/MetagenomeScope/issues/396)).

- Tidy up the README in various ways (e.g. updating screenshots).

### Fixed

- There are extremely rare cases where Graphviz can "lose" an edge and not
  draw it ([#394](https://github.com/marbl/MetagenomeScope/issues/394),
  [issue 1323 on Graphviz' repository](https://gitlab.com/graphviz/graphviz/-/work_items/1323)).
  Detect these cases, log them
  ([#400](https://github.com/marbl/MetagenomeScope/issues/400)),
  and ensure they are at least drawn as a straight line -- so that all
  edges are shown.

- Fix a race condition that was causing the detection of "bad edges" (and
  converting them to straight lines when initially drawing a region of the
  graph) to not trigger properly ([commit `9810ae0`](https://github.com/marbl/MetagenomeScope/commit/9810ae0a506376b83921277ce13858eb20fecfa0)).

- There are very rare cases where an edge can be routed into the middle of
  nowhere ([#406](https://github.com/marbl/MetagenomeScope/issues/406)).
  As with the other types of problematic edges, detect these cases, log them,
  and flatten them into straight lines.

- Prevent node / edge names that start with `--`
  ([#402](https://github.com/marbl/MetagenomeScope/issues/402)).

- Include additional JavaScript dependencies to make sure that the dagre
  and fCoSE layout methods work consistently
  ([#397](https://github.com/marbl/MetagenomeScope/issues/397)).

- Update the `metagenomescope/tests/README.md` file to reflect the switch
  from `setup.py` to `pyproject.toml`.


## [v1.1.0] - 2026-03-05 - Documentation and refactoring
[v1.1.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v1.1.0

### Added

- Add documentation to the README on patterns, boundary node splitting, etc.

### Changed

- Lower default screenshot scaling factor from 5x to 2x.

- Remove Dash Cytoscape as a dependency; replace it with custom JavaScript code
  that interfaces with Cytoscape.js.
  ([#362](https://github.com/marbl/MetagenomeScope/issues/362))

### Fixed

- Now that we are no longer bound to Dash Cytoscape, this allowed us to upgrade
  the Cytoscape.js version in use to v3.31.4. This addresses
  [#262](https://github.com/marbl/MetagenomeScope/issues/262).

- A few minor development improvements (e.g. using both `license` and
  `license-files` in the `pyproject.toml` file).


## [v1.0.0] - 2026-02-23 - First official release!
[v1.0.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v1.0.0

Restructures MetagenomeScope as a server-side application using Dash.
Implements many long-awaited features, including hierarchical pattern
decomposition, detailed charts of graph statistics, and much more.


## [v0.1.0] - 2020-11-30 - "Classic" MetagenomeScope
[v0.1.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v0.1.0

This is an old version of MetagenomeScope's code, tagged as a release for
posterity. Many of its features will be added back in to newer versions of
MetagenomeScope fairly soon, but some features (e.g. SPQR tree decomposition)
may not be included in the new versions for some time (or at all) due to time
constraints.

Some artifacts from this old version of MetagenomeScope, for the record:

- [Undergrad thesis](https://fedarko.github.io/res/docs/mgsc_thesis.pdf) (2018)

- [Poster](https://marbl.github.io/MetagenomeScope/res/gd2017_mgsc_poster_updated.pdf)
  and
  [poster abstract](https://link.springer.com/book/10.1007/978-3-319-73915-1)
  ([GD 2017](https://gd2017.khoury.northeastern.edu/))
