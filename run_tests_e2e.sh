#!/usr/bin/env bash
uv run pytest tests/e2e/ -v --tb=short 2>&1
