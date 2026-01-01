# MetagenomeScope Tests

This directory contains test code for MetagenomeScope.

## Running Tests

From the root of the MetagenomeScope repository, run `make test`.

### Notes About Running Tests

* Requires [pytest](https://pytest.org/). See the extra dependencies marked as `dev`
  in MetagenomeScope's `setup.py`.

* We assume tests are run from the root of the MetagenomeScope repository -- running
  them from elsewhere will probably cause them to fail.

## Test data acknowledgements

See the README in the [`input/`](https://github.com/marbl/MetagenomeScope/tree/main/metagenomescope/tests/input) directory.
