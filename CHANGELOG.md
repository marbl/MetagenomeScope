# Changelog

All notable changes to this project will be documented in this file.

As inspired by [Pyrodigal](https://github.com/althonos/pyrodigal),
this format is adapted from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
[Unreleased]: https://github.com/marbl/MetagenomeScope/compare/v1.1.0...HEAD

### Added

- Add a new drawing method, `Entire graph (nonredundant)`
  ([#67](https://github.com/marbl/MetagenomeScope/issues/67)).

  In most common assembly graph formats (e.g. GFA), there exist reverse-
  complementary pairs of nodes and edges (e.g. `X` and `-X`, `X -> Y` and
  `-Y -> -X`). Often entire connected components are reverse-complementary
  in this way; in such cases, drawing both components is not usually necessary.

  This drawing method detects pairs of "redundant" reverse-complementary
  components, and will draw (1) all "nonredundant" components and (2) one
  arbitrary component from each pair of "redundant" components. This way, you
  can visualize the "unique" parts of the graph without having to draw a bunch
  of unnecessary components.

- Various updates to the README, including bioconda installation instructions!
  ([#302](https://github.com/marbl/MetagenomeScope/issues/302))

- Add this Changelog.

### Changed

- Change how random colors are assigned to edges in DOT files
  ([#401](https://github.com/marbl/MetagenomeScope/issues/401)).
  Previously, the random colors were assigned based on the surrounding nodes
  of an edge, so that all edges `X -> Y` and `-Y -> -X` (including parallel
  edges) were assigned the same random color.

  However, in Flye DOT files, nodes don't have orientations, so this meant that
  an edge `E` and its reverse-complement `-E` were not necessarily being
  assigned the same random color. I've fixed this so that random colors are
  instead assigned based on edge ID, so that edges `E` and `-E` are guaranteed
  to be assigned the same random color. This should result in clearer-looking
  drawings.

- The icons used to represent layout algorithms in the "drawing options" dialog
  are now drawn with slightly thicker strokes. Um, in case that is relevant to
  you. Probably not.

### Fixed

- There are extremely rare cases where Graphviz can "lose" an edge and not
  draw it ([#394](https://github.com/marbl/MetagenomeScope/issues/394),
  [issue 1323 on Graphviz' repository](https://gitlab.com/graphviz/graphviz/-/work_items/1323)).
  Detect these cases and ensure they are at least drawn
  as a straight line, so that all edges are shown.

- Fix a race condition that was causing the detection of "bad edges" (and
  converting them to straight lines when initially drawing a region of the
  graph) to not trigger properly ([commit `9810ae0`](https://github.com/marbl/MetagenomeScope/commit/9810ae0a506376b83921277ce13858eb20fecfa0)).

- Prevent node / edge names that start with `--`
  ([#402](https://github.com/marbl/MetagenomeScope/issues/402)).

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
