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

from setuptools import find_packages, setup

classes = """
    Development Status :: 3 - Alpha
    License :: OSI Approved :: GNU GPL 3 License
    Topic :: Software Development :: Libraries
    Topic :: Scientific/Engineering
    Topic :: Scientific/Engineering :: Bio-Informatics
    Topic :: Scientific/Engineering :: Visualization
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3 :: Only
    Operating System :: Unix
    Operating System :: POSIX
    Operating System :: MacOS :: MacOS X
"""
classifiers = [s.strip() for s in classes.split("\n") if s]

description = "Visualization tool for metagenomic assembly graphs"

long_description = (
    "MetagenomeScope is a web-based visualization tool for "
    "metagenomic assembly graphs. It focuses on presenting "
    "a hierarchical layout of the graph that emphasizes "
    "a semilinear display alongside highlighting various "
    "structural patterns within the graph."
)

version = "0.1.0-dev"

setup(
    name="metagenomescope",
    version=version,
    license="GPL3",
    description=description,
    long_description=long_description,
    author="MetagenomeScope Development Team"
    author_email="mfedarko@ucsd.edu",
    maintainer="Marcus Fedarko",
    maintainer_email="mfedarko@ucsd.edu",
    url="https://github.com/marbl/MetagenomeScope",
    classifiers=classifiers,
    packages=find_packages(),
    package_data={"metagenomescope": ["support_files"]},
    include_package_data=True,
    # Sanity check before trying to install -- these should be installed with
    # the parent conda environment
    setup_requires=["numpy", "pygraphviz"],
    install_requires=[
        "click",
        "numpy",
        "networkx",
        "gfapy",
        "pyfastg",
        "jinja2",
    ],
    # The reason I pin the black version to at least 22.1.0 is that this
    # version changes how the ** operator is formatted (no surrounding spaces,
    # usually). Not being consistent causes the build to fail, hence the pin.
    extras_require={
        "dev": ["pytest", "pytest-cov", "flake8", "black>=22.1.0"]
    },
    entry_points={"console_scripts": ["mgsc=metagenomescope._cli:run_script"]},
    zip_safe=False,
)
