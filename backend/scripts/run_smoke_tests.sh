#!/bin/bash

# VoiceApp Backend Smoke Tests Runner
# ===================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BASE_URL="http://localhost:8000"
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "VoiceApp Backend Smoke Tests"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --base-url URL    API base URL (default: http://localhost:8000)"
      echo "  --verbose, -v     Enable verbose output"
      echo "  --help, -h        Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                                    # Test local server"
      echo "  $0 --base-url https://api.voiceapp.com  # Test production"
      echo "  $0 --verbose                         # Detailed output"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}🔥 VoiceApp Backend Smoke Tests${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if the script is being run from the project root
if [[ ! -f "main.py" ]]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
    echo "Expected to find main.py in the current directory"
    exit 1
fi

# Check if Python virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -f "venv/bin/activate" ]]; then
    echo -e "${YELLOW}⚠️ Warning: No virtual environment detected${NC}"
    echo "Consider running: python -m venv venv && source venv/bin/activate"
    echo ""
fi

# Install dependencies if needed
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! python -c "import aiohttp, websockets, firebase_admin" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ Installing missing dependencies...${NC}"
    pip install aiohttp websockets firebase-admin requests
fi

# Check if server is running
echo -e "${BLUE}🔍 Checking server status...${NC}"
if curl -s "$BASE_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is responding at $BASE_URL${NC}"
else
    echo -e "${YELLOW}⚠️ Server may not be running at $BASE_URL${NC}"
    echo "Consider starting the server with: python main.py"
    echo "Continuing with tests anyway..."
fi

echo ""

# Run the smoke tests
echo -e "${BLUE}🚀 Running smoke tests...${NC}"
echo ""

SMOKE_TEST_ARGS="--base-url $BASE_URL"
if [[ "$VERBOSE" == "true" ]]; then
    SMOKE_TEST_ARGS="$SMOKE_TEST_ARGS --verbose"
fi

# Execute the smoke test
if python scripts/smoke_test.py $SMOKE_TEST_ARGS; then
    echo ""
    echo -e "${GREEN}🎉 All smoke tests completed successfully!${NC}"
    exit 0
else
    exit_code=$?
    echo ""
    if [[ $exit_code -eq 1 ]]; then
        echo -e "${YELLOW}⚠️ Smoke tests completed with warnings${NC}"
    else
        echo -e "${RED}💥 Smoke tests failed${NC}"
    fi
    exit $exit_code
fi 