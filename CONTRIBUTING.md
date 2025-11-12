# MetagenomeScope development documentation

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

## Helpful development commands

(You should run these from the root directory of the repository.)

```bash
# Run tests
make test

# Run linting / stylechecking
make stylecheck

# Autoformat code
make style
```
