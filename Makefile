.PHONY: help install install-dev test lint format clean build install-tools run-example

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install the package and dependencies"
	@echo "  install-dev   - Install in development mode with dev dependencies"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with black"
	@echo "  clean         - Clean build artifacts"
	@echo "  build         - Build distribution packages"
	@echo "  install-tools - Install external tools (kubent, pluto)"
	@echo "  run-example   - Run example assessment"

# Install the package
install:
	pip install -r requirements.txt
	pip install -e .

# Install in development mode
install-dev:
	pip install -r requirements.txt
	pip install -e .
	pip install pytest black flake8 mypy

# Run tests
test:
	python -m pytest tests/ -v

# Run linting
lint:
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports

# Format code
format:
	black src/ tests/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build distribution packages
build: clean
	python setup.py sdist bdist_wheel

# Install external tools
install-tools:
	@echo "Installing external tools..."
	chmod +x install-tools.sh
	./install-tools.sh

# Run example assessment
run-example:
	@echo "Running example assessment..."
	python src/main.py --config eks-upgrade-config.yaml

# Setup development environment
setup-dev: install-dev install-tools
	@echo "Development environment setup complete!"

# Run all checks
check: lint test
	@echo "All checks passed!"
