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

### Running the visualization in debug mode

The [`metagenomescope/tests/input/`](https://github.com/marbl/MetagenomeScope/tree/main/metagenomescope/tests/input)
directory contains various graphs and
associated files that may be helpful in testing out your changes.

For example, here is how we might test out MetagenomeScope using a small
yeast assembly graph from Flye (the graph is from
[AGB](https://github.com/almiheenko/AGB/tree/master/test_data/flye_yeast)'s repository):

```bash
mgsc \
    -g metagenomescope/tests/input/flye_yeast.gv \
    -a metagenomescope/tests/input/flye_yeast.agp \
    --verbose \
    --debug
```

Using `--debug` is nice because it enables
[Dash Dev Tools](https://dash.plotly.com/devtools). This will enable useful features
like hot reloading (whenever you changed code, Dash should reload the application).

Note that using `--debug` will process the graph twice on startup. This appears
to just be a Dash thing. So, if you are testing out how MetagenomeScope works on
a massive graph where processing it will take a while, using `--debug` may not be
ideal.

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
