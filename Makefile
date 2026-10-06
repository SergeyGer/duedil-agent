# Using a non-tab recipe prefix keeps this Makefile portable across editors/OSes.
.RECIPEPREFIX = >

VENV ?= .venv
ifeq ($(OS),Windows_NT)
PY := $(VENV)/Scripts/python.exe
else
PY := $(VENV)/bin/python
endif

.PHONY: help install test cov lint fmt run demo docker-build docker-run docker-demo docker-cli clean

help:
> @echo "DueDil.Agent - available targets:"
> @echo "  install      create the virtualenv and install dependencies"
> @echo "  test         run the test suite"
> @echo "  cov          run tests with a coverage report"
> @echo "  lint         run ruff check"
> @echo "  fmt          run ruff format"
> @echo "  run          launch the Streamlit UI"
> @echo "  demo         run the offline demo pipeline (no API keys)"
> @echo "  docker-build build the Docker image"
> @echo "  docker-run   run the web UI in Docker (http://localhost:8501)"
> @echo "  docker-demo  run the Docker image in offline demo mode"
> @echo "  docker-cli   run the CLI in Docker on the bundled sample deck"
> @echo "  clean        remove caches"

install:
> python -m venv $(VENV)
> $(PY) -m pip install --upgrade pip
> $(PY) -m pip install -r requirements.txt

test:
> $(PY) -m pytest

cov:
> $(PY) -m pytest --cov=app --cov-report=term-missing

lint:
> $(PY) -m ruff check .

fmt:
> $(PY) -m ruff format .

run:
> $(PY) -m streamlit run app/ui.py

demo:
> $(PY) scripts/demo_offline.py

docker-build:
> docker build -t duedil-agent:latest .

docker-run:
> docker run --rm -p 8501:8501 --env-file .env duedil-agent:latest

docker-demo:
> docker run --rm -p 8501:8501 -e DUEDIL_MODE=demo-ui duedil-agent:latest

docker-cli:
> docker run --rm --env-file .env -v "$(PWD)/examples:/app/examples:ro" duedil-agent:latest \
>   python -m app.cli examples/sample_deck.pdf https://nimbusai.example

clean:
> -rm -rf .pytest_cache .ruff_cache htmlcov .coverage
> -find . -name "__pycache__" -type d -prune -exec rm -rf {} +
