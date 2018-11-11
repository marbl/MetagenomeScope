# MetagenomeScope Tests

This directory contains test code for MetagenomeScope. As you can see, there
aren't a lot of these yet; I'm planning on adding a lot more. The current tests
only cover the preprocessing script so far, but I'm planning on adding some
for the viewer interface as well.

## Running Tests

From the root of the MetagenomeScope repository, run `make generaltest` to test
everything but the `-spqr` tests and `make spqrtest` to test things specific to
the `-spqr` option (which has some extra installation requirements). You can
also just run `make test` to run both types of tests.

### Notes About Running Tests

* All of these commands require [pytest](https://pytest.org/) to be
  installed.

* These commands all assume they're being run from the root of the
  MetagenomeScope repository -- running them from elsewhere will probably cause
  them to fail.

* After running `make generaltest` or `make spqrtest`, the `tests/output`
  directory will be emptied (to avoid buildup of test files on your system).
  You can disable this behavior by removing the "rm tests/output/\*" lines from the
  corresponding targets in the Makefile.

## Test Data Acknowledgements (`input/`)

`loop.gfa` was created by Shaun Jackman.
[Here](https://github.com/sjackman/assembly-graph/blob/fef9fada23ddfb3da04db8221fac1ca8c99bfc66/loop.gfa)
is a link to the version of the file used.
