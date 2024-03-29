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

`sample1.gfa` and `sample2.gfa` were also created by Shaun Jackman, and were
downloaded from the [gfalint](https://github.com/sjackman/gfalint) repository
(in the `examples/` folder).

`marygold_fig2a.gml` is based on Figure 2a from
[Nijkamp et al. 2013](https://www.ncbi.nlm.nih.gov/pubmed/24058058).

`E_coli_LastGraph` is a modified version of one of
[Bandage's](http://rrwick.github.io/Bandage/)
sample graphs, which apparently was created from data located on NCBI
[here](https://www.ncbi.nlm.nih.gov/sra?linkname=bioproject_sra_all&from_uid=272917).
The version included here has been modified so that every node's sequence has
just been changed to `ACGT` -- this is because we don't really care about the
actual sequence data for the tests here so much as the topology of the graph
(so there's no reason to store like 9 MB of sequence data).

<!-- TODO: add a ref to the strainFlye paper eventually -->
`sheepgut_g1217.gfa` corresponds to a small, highly-mutated region of a MAG
"smoothed-read" assembly graph generated from the sheep gut dataset used in
[Bickhart and Kolmogorov et al. 2022](https://www.nature.com/articles/s41587-021-01130-z).
