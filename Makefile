# Phony targets in this file:
#
# test: Runs the python and js tests.
#
# pytest: Runs all preprocessing script tests using pytest.
#
# jstest: Instruments the JS files for code coverage and runs JS tests using
#  mocha-headless-chrome.
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

.PHONY: pytest jstest test pystylecheck jsstylecheck stylecheck pystyle jsstyle style demo

PYLOCS = metagenomescope/ setup.py
JSLOCS = metagenomescope/support_files/js/*.js metagenomescope/tests/js_tests/*.js docs/js/extra_functionality.js .jshintrc
HTMLCSSLOCS = metagenomescope/support_files/index.html metagenomescope/tests/js_tests/*.html metagenomescope/support_files/css/viewer_style.css docs/404.html docs/index.html docs/css/mgsc_docs_style.css

# -B: don't create __pycache__/ directories
pytest:
	python3 -B -m pytest \
		metagenomescope/tests/ \
		--cov-report xml \
		--cov-report term \
		--cov-report html \
		--cov metagenomescope

jstest:
	nyc instrument metagenomescope/support_files/js/ metagenomescope/tests/js_tests/instrumented_js/
	mocha-headless-chrome -f metagenomescope/tests/js_tests/index.html -c js_coverage.json

test: pytest jstest

pystylecheck:
	flake8 --ignore=E203,W503,E266,E501 $(PYLOCS)
	black --check -l 79 $(PYLOCS)

jsstylecheck:
	jshint $(JSLOCS)
	prettier --check --tab-width 4 $(JSLOCS) $(HTMLCSSLOCS)

stylecheck: pystylecheck jsstylecheck

pystyle:
	black -l 79 $(PYLOCS)

jsstyle:
	@# Shorthand, for when I'm developing JS code and don't want to waste time
	@# with python/HTML stuff
	prettier --write --tab-width 4 $(JSLOCS)

style: pystyle jsstyle

demo:
	@# makes a simple demo with a tiny graph that lets us test out the viewer
	@# interface
	rm -rf mg2
	mgsc -i metagenomescope/tests/input/sample1.gfa -o mg2
