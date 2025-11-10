# Phony targets in this file:
#
# test: Runs the python and js tests.
#
# pytest: Runs all preprocessing script tests using pytest.
#
# stylecheck: Checks to make sure that the Python and JavaScript codebases are
#  properly formatted. Requires that a few extra packages are installed.
#
# style: Auto-formats code to make it (mostly) compliant with stylecheck.
#  Requires that a few extra packages are installed.
#
# Many of these directives were based on Qurro's Makefile (which was kind of
# based on the initial version of this Makefile, anyway, so it's a silly
# chicken-and-egg thing).

.PHONY: pytest test pystylecheck stylecheck pystyle style demo

PYLOCS = metagenomescope/ setup.py

# -B: don't create __pycache__/ directories
pytest:
	python3 -B -m pytest \
		metagenomescope/tests/ \
		--cov-report xml \
		--cov-report term \
		--cov-report html \
		--cov metagenomescope

test: pytest

pystylecheck:
	flake8 --ignore=E203,W503,E266,E501 $(PYLOCS)
	black --check -l 79 $(PYLOCS)

stylecheck: pystylecheck jsstylecheck

pystyle:
	black -l 79 $(PYLOCS)

style: pystyle

demo:
	@# makes a simple demo with a tiny graph that lets us test out the viz
	mgsc -g metagenomescope/tests/input/sample1.gfa --verbose
