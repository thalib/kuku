#!/usr/bin/env bash

show_help() {
    echo -e "\033[36mUsage: ./run_tests.sh [option]\033[0m"
    echo ""
    echo -e "\033[33mOptions:\033[0m"
    echo "  --all     Run all tests"
    echo "  --e2e     Run only e2e tests"
    echo "  --unit    Run all tests except e2e"
    echo "  --help    Show this help message (default)"
}

case "${1:-}" in
    --all)
        uv run pytest
        ;;
    --e2e)
        uv run pytest tests/e2e/
        ;;
    --unit)
        uv run pytest --ignore=tests/e2e/
        ;;
    *)
        show_help
        ;;
esac
