.PHONY: test stylecheck style demo

PYLOCS = metagenomescope/

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
