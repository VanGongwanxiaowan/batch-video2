# Makefile for BatchShort project

# Variables
PYTHON = python3.8
PIP = pip3
VENV = venv
PYTEST = pytest -v --cov=./ --cov-report=term-missing

.PHONY: help install-dev install test lint format check-types check-security clean

help:
	@echo "Available commands:"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make install        Install production dependencies"
	@echo "  make test           Run tests with coverage"
	@echo "  make lint           Run linters (flake8, pylint)"
	@echo "  make format         Format code with black and isort"
	@echo "  make check-types    Run type checking with mypy"
	@echo "  make check-security Run security checks with bandit"
	@echo "  make clean          Clean up temporary files"

# Install development dependencies
install-dev:
	$(PIP) install -e ".[dev]"
	pre-commit install

# Install production dependencies
install:
	$(PIP) install -e .

# Run tests
test:
	$(PYTEST) tests/

# Run linters
lint:
	flake8 .
	pylint core/ services/

# Format code
format:
	black .
	isort .

# Run type checking
check-types:
	mypy .

# Run security checks
check-security:
	bandit -r . -c pyproject.toml

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	rm -rf .coverage htmlcov/ build/ dist/ *.egg-info/
