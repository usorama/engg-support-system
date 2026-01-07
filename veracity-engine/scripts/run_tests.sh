#!/bin/bash
#
# Test Runner Script (STORY-016)
#
# Runs the complete test suite with various options.
# Supports CI integration with exit codes and JSON output.
#
# Usage:
#   ./scripts/run_tests.sh           # Run all tests
#   ./scripts/run_tests.sh unit      # Run unit tests only
#   ./scripts/run_tests.sh --ci      # CI mode with coverage
#   ./scripts/run_tests.sh --json    # Output JSON results
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
MODE="all"
CI_MODE=false
JSON_OUTPUT=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|reproducibility)
            MODE="$1"
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [mode] [options]"
            echo ""
            echo "Modes:"
            echo "  all             Run all tests (default)"
            echo "  unit            Run unit tests only"
            echo "  integration     Run integration tests only"
            echo "  reproducibility Run reproducibility tests only"
            echo ""
            echo "Options:"
            echo "  --ci            CI mode (coverage, no capture)"
            echo "  --json          Output JSON results"
            echo "  -v, --verbose   Verbose output"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Build pytest command
PYTEST_CMD="python3 -m pytest"
PYTEST_ARGS=""

# Add verbose if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

# Add CI-specific options
if [ "$CI_MODE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=core --cov-report=term-missing --cov-report=html:coverage_report -s"
fi

# Add JSON output
if [ "$JSON_OUTPUT" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --json-report --json-report-file=test_results.json"
fi

# Select test directory based on mode
case $MODE in
    unit)
        TEST_PATH="tests/ -k 'not integration and not reproducibility'"
        echo -e "${BLUE}Running unit tests...${NC}"
        ;;
    integration)
        TEST_PATH="tests/ -k 'integration'"
        echo -e "${BLUE}Running integration tests...${NC}"
        ;;
    reproducibility)
        TEST_PATH="tests/test_reproducibility.py"
        echo -e "${BLUE}Running reproducibility tests...${NC}"
        ;;
    all)
        TEST_PATH="tests/"
        echo -e "${BLUE}Running all tests...${NC}"
        ;;
esac

# Print command
echo -e "${YELLOW}Command: ${PYTEST_CMD} ${TEST_PATH} ${PYTEST_ARGS}${NC}"
echo ""

# Run tests
if eval "${PYTEST_CMD} ${TEST_PATH} ${PYTEST_ARGS}"; then
    echo ""
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
