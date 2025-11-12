# <a href="https://marbl.github.io/MetagenomeScope/"><img src="https://raw.githubusercontent.com/fedarko/MetagenomeScope-1/refs/heads/desk/metagenomescope/assets/favicon.ico" alt="Icon" /></a> MetagenomeScope development documentation

## Setting up a development environment

First, you should probably fork MetagenomeScope. This will simplify the
process of contributing your changes back to the main branch later.

After that, run the following commands. (These assume that mamba is
installed.)

```bash
# Clone your fork
git clone https://github.com/your-github-username-goes-here/MetagenomeScope.git

# Install conda dependencies
cd MetagenomeScope
mamba create -n mgscdev -c conda-forge "python >= 3.8" numpy pygraphviz
mamba activate mgscdev

# Install MetagenomeScope from the cloned source code in "editable mode"
pip install -e .[dev]
```

At this point, run `mgsc` and `which mgsc` to test that things are installed
correctly.

## Some commands to help with development

(You should run these from the root directory of the repository.)

### Run a simple demo

```bash
make demo
```

The `metagenomescope/tests/input/` directory contains some other
example graph files that may be helpful in testing out your changes.

### Linting and stylechecking

```bash
make stylecheck
```

### Autoformat the code

```bash
make style
```

### Run tests

```bash
make test
```

This command will create a `htmlcov` directory in the root of MetagenomeScope's
code, containing a nice interactive coverage report.
