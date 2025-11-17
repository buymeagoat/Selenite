# Selenite Backend Makefile
# Quality assurance and development automation

.PHONY: help qa qa-quick format lint test coverage clean

help:
	@echo "Selenite Backend - Available targets:"
	@echo "  qa         - Run full quality assurance suite"
	@echo "  qa-quick   - Run fast quality checks (format + lint)"
	@echo "  format     - Auto-format code with black"
	@echo "  lint       - Run ruff linter"
	@echo "  test       - Run all tests"
	@echo "  coverage   - Run tests with coverage report"
	@echo "  clean      - Remove generated files"

qa: format lint test
	@echo "✅ Full QA suite passed!"

qa-quick: format lint
	@echo "✅ Quick QA checks passed!"

format:
	@echo "🔧 Formatting code with black..."
	python -m black app/ tests/

lint:
	@echo "🔍 Running ruff linter..."
	python -m ruff check app/ tests/ --fix

test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

coverage:
	@echo "📊 Running tests with coverage..."
	python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	@echo "🧹 Cleaning generated files..."
	rm -rf htmlcov/ .coverage coverage.xml .pytest_cache/ __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
