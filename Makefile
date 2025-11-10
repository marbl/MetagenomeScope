.PHONY: test stylecheck style demo

PYLOCS = metagenomescope/ setup.py

# -B: don't create __pycache__/ directories
test:
	python3 -B -m pytest \
		metagenomescope/tests/ \
		--cov-report xml \
		--cov-report term \
		--cov-report html \
		--cov metagenomescope

stylecheck:
	flake8 --ignore=E203,W503,E266,E501 $(PYLOCS)
	black --check -l 79 $(PYLOCS)

style:
	black -l 79 $(PYLOCS)

demo:
	@# makes a simple demo with a tiny graph that lets us test out the viz
	mgsc -g metagenomescope/tests/input/sample1.gfa --verbose
