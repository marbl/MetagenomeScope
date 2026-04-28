# Changelog

All notable changes to this project will be documented in this file.

As inspired by [Pyrodigal](https://github.com/althonos/pyrodigal),
this format is adapted from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
[Unreleased]: https://github.com/marbl/MetagenomeScope/compare/v1.2.0...HEAD

### Added

- Add the `-t`/`--vtsv` command-line option, to support reading
  [Verkko](https://github.com/marbl/verkko)-style TSV files describing paths
  ([#336](https://github.com/marbl/MetagenomeScope/issues/336)).

- Add the `--dcheck` command-line flag, which controls whether or not to run
  a sanity check after pattern decomposition that verifies the integrity of
  the graph
  ([#421](https://github.com/marbl/MetagenomeScope/issues/421)).

  - This check involves, among other things, creating an extra copy of the
    input graph structure before decomposition. It can be a bottleneck when
    working with massive graphs on low-memory systems.

- Various updates to the README.

### Changed

- Implement a custom GFA parser. This dramatically speeds up loading GFA files,
  and makes it easier to quietly ignore nonstandard GFA tags
  ([#310](https://github.com/marbl/MetagenomeScope/issues/310),
  [#403](https://github.com/marbl/MetagenomeScope/issues/403)).

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

- Prevent node or edge IDs from beginning with `[N`. This makes parsing Verkko
  TSV files easier: with this restriction, we can now unambiguously say if
  something on a path is a gap or not.

- Add more detail to the `--verbose` log messages during pattern decomposition.

- Turn off the creation of `AssemblyGraph.original_graph`, the call to
  `AssemblyGraph._sanity_check_graph()`, etc. by default; as discussed in
  "Added" above, this is now controlled by the `--dcheck` command-line flag
  ([#421](https://github.com/marbl/MetagenomeScope/issues/421)).

### Fixed

- Clean up and add some more tests for the path-parsing parts of the code.

- Fix a bug where Flye DOT files with split nodes / fake edges remaining
  after the decomposition would crash the redundant component detection
  ([commit `2a87720`](https://github.com/marbl/MetagenomeScope/commit/2a877209c9cfc90755ef4474f47add8b6e387f1b)).


## [v1.2.0] - 2026-03-27 - Nonredundant drawing, bug fixes, and cleaning up
[v1.2.0]: https://github.com/marbl/MetagenomeScope/releases/tag/v1.2.0

### Added

- Add a new drawing method, `Entire graph (nonredundant)`, that draws the
  entire graph _but_ draws perfectly reverse-complementary components
  only once ([#67](https://github.com/marbl/MetagenomeScope/issues/67)).

- Tidy up the README in various ways, including updating screenshots
  and adding bioconda installation instructions
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

- Clean up the internal formatting of edge control points
  ([#396](https://github.com/marbl/MetagenomeScope/issues/396)).

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
