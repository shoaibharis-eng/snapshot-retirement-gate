PYTHON ?= python3

.PHONY: check test demo lint

# Everything a reviewer needs. Uses the standard library only.
check: test demo

test:
	$(PYTHON) -m unittest

demo:
	$(PYTHON) -m reproduction

# Optional. Needs ruff: pip install ruff
lint:
	ruff check .
	ruff format --check .
