.PHONY: test test-ci test-all backend-test frontend-check

# Fast CI-style checks (no network integration tests)
test-ci:
	cd backend && ruff check app tests && PYTHONPATH=. pytest -q -m "not integration"
	cd frontend && npm ci && npm run lint && npm run build

# Everything including SEC/yfinance smoke tests (slow; needs network)
test-all:
	cd backend && ruff check app tests && PYTHONPATH=. pytest -v
	cd frontend && npm ci && npm run lint && npm run build

# Alias: default `make test` matches CI
test: test-ci

backend-test:
	cd backend && PYTHONPATH=. pytest -v -m "not integration"

frontend-check:
	cd frontend && npm run lint && npm run build
