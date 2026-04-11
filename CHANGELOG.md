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

- Various updates to the README.

### Changed

- Prevent node or edge IDs from beginning with `[N`. This removes ambiguity
  when parsing Verkko TSV files.

### Fixed

- Cleaned up and added some more tests for the path-parsing parts of the code.


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
