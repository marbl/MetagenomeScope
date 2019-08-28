#!/usr/bin/env python2.7
# Copyright (C) 2017-2019 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
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

import re
import ast
from setuptools import find_packages, setup

classes = """
    Development Status :: 3 - Alpha
    License :: OSI Approved :: GNU GPL 3 License
    Topic :: Software Development :: Libraries
    Topic :: Scientific/Engineering
    Topic :: Scientific/Engineering :: Bio-Informatics
    Topic :: Scientific/Engineering :: Visualization
    Programming Language :: Python :: 2
    Programming Language :: Python :: 2 :: Only
    Operating System :: Unix
    Operating System :: POSIX
    Operating System :: MacOS :: MacOS X
"""
classifiers = [s.strip() for s in classes.split('\n') if s]

description = "Visualization tool for metagenomic assembly graphs"

long_description = ("MetagenomeScope is a web-based visualization tool for "
                    "metagenomic assembly graphs. It focuses on presenting "
                    "a hierarchical layout of the graph that emphasizes "
                    "a semilinear display alongside highlighting various "
                    "structural patterns within the graph.")

# version parsing from __init__ pulled from Flask's setup.py
# https://github.com/mitsuhiko/flask/blob/master/setup.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

version = "0.0.0"

setup(
    name="metagenomescope",
    version=version,
    license='GPL3',
    description=description,
    long_description=long_description,
    author="Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop",
    author_email="mfedarko@ucsd.edu",
    maintainer="Marcus Fedarko",
    maintainer_email="mfedarko@ucsd.edu",
    packages=find_packages(),
    install_requires=["pygraphviz", "numpy"],
    extras_require={"dev": ["pytest"]},
    classifiers=classifiers,
    entry_points={
        'console_scripts': ['mgsc=metagenomescope.collate:run_script']
    },
    zip_safe=False
)
