# MetagenomeScope Tests

This directory contains test code for MetagenomeScope. As you can see, there
aren't a lot of these yet; I'm planning on adding a lot more. The current tests
only cover the preprocessing script so far, but I'm planning on adding some
for the viewer interface as well.

## Running Tests

From the root of the MetagenomeScope repository, run `make test`. This requires
that pytest is installed.

These tests assume that pytest is being run from the root of the
MetagenomeScope repository -- running pytest from elsewhere on these tests
will probably cause them to fail.

## Test Data Acknowledgements

`loop.gfa` was created by Shaun Jackman.
[Here](https://github.com/sjackman/assembly-graph/blob/fef9fada23ddfb3da04db8221fac1ca8c99bfc66/loop.gfa)
is a link to the version of the file used.
