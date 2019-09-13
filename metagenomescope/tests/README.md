# MetagenomeScope Preprocessing Script Tests

This directory contains test code for MetagenomeScope's preprocessing script.
As you can see, there aren't a lot of these yet; I'm planning on adding a lot
more.

## Running Tests

From the root of the MetagenomeScope repository, run `make pytest` to test
all preprocessing script tests and run `make spqrtest` to test things specific
to the `-spqr` option (which has some extra installation requirements).

### Notes About Running Tests

* All of these commands require [pytest](https://pytest.org/) to be
  installed.

* These various `make test` commands all assume they're being run from the root of
  the MetagenomeScope repository -- running them from elsewhere will probably cause
  them to fail.

## Test Data Acknowledgements (`input/`)

`loop.gfa` was created by Shaun Jackman.
[Here](https://github.com/sjackman/assembly-graph/blob/fef9fada23ddfb3da04db8221fac1ca8c99bfc66/loop.gfa)
is a link to the version of the file used.
