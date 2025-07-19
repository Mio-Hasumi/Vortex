#!/bin/bash

# VoiceApp Test Runner Script
# Runs all test suites: Unit, Integration, and Contract tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Parse command line arguments
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_CONTRACT=false
RUN_ALL=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_CONTRACT=false
            shift
            ;;
        --integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            RUN_CONTRACT=false
            shift
            ;;
        --contract)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_CONTRACT=true
            shift
            ;;
        --all)
            RUN_ALL=true
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_CONTRACT=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --unit        Run only unit tests (default)"
            echo "  --integration Run only integration tests"
            echo "  --contract    Run only contract tests"
            echo "  --all         Run all test suites"
            echo "  --verbose, -v Verbose output"
            echo "  --help, -h    Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "🧪 VoiceApp Test Suite Runner"
echo "=================================="

# Check dependencies
print_status "Checking dependencies..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

if ! command_exists pip; then
    print_error "pip is required but not installed."
    exit 1
fi

# Install test dependencies if needed
print_status "Installing test dependencies..."
pip install -r requirements-test.txt --quiet

# Set test verbosity
PYTEST_ARGS="-v"
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="-vv --tb=long"
else
    PYTEST_ARGS="-v --tb=short"
fi

# Track test results
UNIT_RESULT=0
INTEGRATION_RESULT=0
CONTRACT_RESULT=0
OVERALL_RESULT=0

# Run Unit Tests
if [ "$RUN_UNIT" = true ]; then
    print_status "🔬 Running Unit Tests..."
    echo "========================"
    
    if pytest tests/unit/ $PYTEST_ARGS --cov=. --cov-report=term-missing; then
        print_success "Unit tests passed!"
        UNIT_RESULT=0
    else
        print_error "Unit tests failed!"
        UNIT_RESULT=1
        OVERALL_RESULT=1
    fi
    echo ""
fi

# Run Integration Tests
if [ "$RUN_INTEGRATION" = true ]; then
    print_status "🔗 Running Integration Tests..."
    echo "==============================="
    
    # Check if server is running
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_status "Server is already running, using existing instance"
        SERVER_RUNNING=true
    else
        print_status "Starting server for integration tests..."
        python3 main.py &
        SERVER_PID=$!
        SERVER_RUNNING=false
        
        # Wait for server to start
        print_status "Waiting for server to start..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/ > /dev/null 2>&1; then
                print_success "Server started successfully"
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
                print_error "Server failed to start within 30 seconds"
                kill $SERVER_PID 2>/dev/null || true
                exit 1
            fi
        done
    fi
    
    # Run integration tests
    if pytest tests/integration/ $PYTEST_ARGS; then
        print_success "Integration tests passed!"
        INTEGRATION_RESULT=0
    else
        print_error "Integration tests failed!"
        INTEGRATION_RESULT=1
        OVERALL_RESULT=1
    fi
    
    # Stop server if we started it
    if [ "$SERVER_RUNNING" = false ] && [ ! -z "$SERVER_PID" ]; then
        print_status "Stopping test server..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    echo ""
fi

# Run Contract Tests
if [ "$RUN_CONTRACT" = true ]; then
    print_status "📋 Running Contract Tests..."
    echo "============================="
    
    # Check if server is running
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_status "Server is already running, using existing instance"
        SERVER_RUNNING=true
    else
        print_status "Starting server for contract tests..."
        python3 main.py &
        SERVER_PID=$!
        SERVER_RUNNING=false
        
        # Wait for server to start
        print_status "Waiting for server to start..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/ > /dev/null 2>&1; then
                print_success "Server started successfully"
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
                print_error "Server failed to start within 30 seconds"
                kill $SERVER_PID 2>/dev/null || true
                exit 1
            fi
        done
    fi
    
    # Run contract tests
    if pytest tests/contract/ $PYTEST_ARGS; then
        print_success "Contract tests passed!"
        
        # Run schemathesis if available
        if command_exists schemathesis; then
            print_status "Running schemathesis automated tests..."
            if schemathesis run http://localhost:8000/openapi.json \
                --checks all \
                --max-examples=5 \
                --hypothesis-deadline=5000 \
                --exclude-path="/api/auth/*" \
                --exclude-path="/api/rooms/*" \
                --exclude-path="/api/matching/*" \
                --exclude-path="/api/friends/*" \
                --exclude-path="/api/recordings/*"; then
                print_success "Schemathesis tests passed!"
            else
                print_warning "Schemathesis tests failed (non-critical)"
            fi
        else
            print_warning "Schemathesis not installed, skipping automated API tests"
        fi
        
        CONTRACT_RESULT=0
    else
        print_error "Contract tests failed!"
        CONTRACT_RESULT=1
        OVERALL_RESULT=1
    fi
    
    # Stop server if we started it
    if [ "$SERVER_RUNNING" = false ] && [ ! -z "$SERVER_PID" ]; then
        print_status "Stopping test server..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    echo ""
fi

# Print summary
print_status "📊 Test Results Summary"
echo "======================="

if [ "$RUN_UNIT" = true ]; then
    if [ $UNIT_RESULT -eq 0 ]; then
        print_success "✅ Unit Tests: PASSED"
    else
        print_error "❌ Unit Tests: FAILED"
    fi
fi

if [ "$RUN_INTEGRATION" = true ]; then
    if [ $INTEGRATION_RESULT -eq 0 ]; then
        print_success "✅ Integration Tests: PASSED"
    else
        print_error "❌ Integration Tests: FAILED"
    fi
fi

if [ "$RUN_CONTRACT" = true ]; then
    if [ $CONTRACT_RESULT -eq 0 ]; then
        print_success "✅ Contract Tests: PASSED"
    else
        print_error "❌ Contract Tests: FAILED"
    fi
fi

echo ""
if [ $OVERALL_RESULT -eq 0 ]; then
    print_success "🎉 All tests passed!"
else
    print_error "💥 Some tests failed!"
fi

exit $OVERALL_RESULT 