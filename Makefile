# Using a non-tab recipe prefix keeps this Makefile portable across editors/OSes.
.RECIPEPREFIX = >

VENV ?= .venv
ifeq ($(OS),Windows_NT)
PY := $(VENV)/Scripts/python.exe
else
PY := $(VENV)/bin/python
endif

.PHONY: help install test cov lint fmt run clean

help:
> @echo "DueDil.Agent - available targets:"
> @echo "  install  create the virtualenv and install dependencies"
> @echo "  test     run the test suite"
> @echo "  cov      run tests with a coverage report"
> @echo "  lint     run ruff check"
> @echo "  fmt      run ruff format"
> @echo "  run      launch the Streamlit UI"
> @echo "  clean    remove caches"

install:
> python -m venv $(VENV)
> $(PY) -m pip install --upgrade pip
> $(PY) -m pip install -r requirements.txt

test:
> $(PY) -m pytest

cov:
> $(PY) -m pytest --cov=app --cov-report=term-missing

lint:
> $(PY) -m ruff check app tests

fmt:
> $(PY) -m ruff format app tests

run:
> $(PY) -m streamlit run app/ui.py

clean:
> -rm -rf .pytest_cache .ruff_cache htmlcov .coverage
> -find . -name "__pycache__" -type d -prune -exec rm -rf {} +
