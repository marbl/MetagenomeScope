#!/usr/bin/env python3
# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
####
# NOTE: This file is derived from Qurro's setup.py file.

import os
from setuptools import find_packages, setup

classes = """
    Development Status :: 3 - Alpha
    License :: OSI Approved :: GNU GPL 3 License
    Topic :: Scientific/Engineering
    Topic :: Scientific/Engineering :: Bio-Informatics
    Topic :: Scientific/Engineering :: Visualization
    Programming Language :: Python :: 3 :: Only
    Operating System :: Unix
    Operating System :: POSIX
    Operating System :: MacOS :: MacOS X
"""
classifiers = [s.strip() for s in classes.split("\n") if s]

description = "Visualization tool for (meta)genome assembly graphs"

long_description = (
    "MetagenomeScope is a web-based visualization tool for "
    "metagenome assembly graphs. It focuses on presenting "
    "a semilinear layout of the graph that highlights "
    "common structural patterns."
)

# Adapted from technique #1 at
# https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
# -- we can't just import __version__ from metagenomescope, because our
# top-level __init__.py imports other modules that depend on packages that
# probably haven't been installed yet at this point in setup (see technique #6
# at the aforementioned website).
__version__ = None
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "metagenomescope", "__init__.py"), "r") as fp:
    for line in fp.readlines():
        if line.startswith('__version__ = "'):
            __version__ = line.split('"')[1]
if __version__ is None:
    raise RuntimeError("Couldn't find version string?")

setup(
    name="metagenomescope",
    version=__version__,
    license="GPL3",
    description=description,
    long_description=long_description,
    author="MetagenomeScope Development Team",
    author_email="mfedarko@umd.edu",
    maintainer="Marcus Fedarko",
    maintainer_email="mfedarko@umd.edu",
    url="https://github.com/marbl/MetagenomeScope",
    classifiers=classifiers,
    packages=find_packages(),
    package_data={"metagenomescope": ["assets"]},
    include_package_data=True,
    # Sanity check before trying to install -- these should be installed with
    # the parent conda environment
    setup_requires=["numpy", "pygraphviz"],
    # NOTE I don't impose minimum versions here yet, but I probably should
    install_requires=[
        "click",
        "numpy",
        "pandas",
        "networkx",
        "gfapy",
        "pyfastg",
        "dash-cytoscape",
    ],
    # The reason I pin the black version to at least 22.1.0 is that this
    # version changes how the ** operator is formatted (no surrounding spaces,
    # usually). Not being consistent causes the build to fail, hence the pin.
    extras_require={
        "dev": ["pytest", "pytest-cov", "flake8", "black>=22.1.0"]
    },
    entry_points={"console_scripts": ["mgsc=metagenomescope._cli:run_script"]},
    # Based on dash-cytoscape's min python version.
    python_requires=">=3.8",
)
