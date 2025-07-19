#!/bin/bash

# VoiceApp Complete Test & Documentation Pipeline
# ==============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
BASE_URL="http://localhost:8000"
VERBOSE=false
SKIP_DOCS=false
SKIP_SMOKE=false
OUTPUT_DIR="./docs"

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
    --skip-docs)
      SKIP_DOCS=true
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=true
      shift
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --help|-h)
      echo -e "${CYAN}VoiceApp Complete Test & Documentation Pipeline${NC}"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --base-url URL       API base URL (default: http://localhost:8000)"
      echo "  --verbose, -v        Enable verbose output"
      echo "  --skip-docs          Skip documentation generation"
      echo "  --skip-smoke         Skip smoke tests"
      echo "  --output-dir DIR     Documentation output directory (default: ./docs)"
      echo "  --help, -h           Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                                    # Full pipeline on local server"
      echo "  $0 --base-url https://api.voiceapp.com  # Test production"
      echo "  $0 --skip-docs                       # Only run smoke tests"
      echo "  $0 --verbose --output-dir ./api-docs # Detailed output, custom docs dir"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to print section headers
print_section() {
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    print_section "🔍 Checking Prerequisites"
    
    # Check if running from project root
    if [[ ! -f "main.py" ]]; then
        echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
        echo "Expected to find main.py in the current directory"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Running from project root${NC}"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Error: Python is not installed${NC}"
        exit 1
    fi
    
    python_version=$($PYTHON_CMD --version 2>&1)
    echo -e "${GREEN}✅ Python found: $python_version${NC}"
    
    # Check virtual environment
    if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -f "venv/bin/activate" ]]; then
        echo -e "${YELLOW}⚠️ Warning: No virtual environment detected${NC}"
        echo "Consider running: python -m venv venv && source venv/bin/activate"
    else
        echo -e "${GREEN}✅ Virtual environment detected${NC}"
    fi
    
    # Install missing dependencies
    echo -e "${BLUE}📦 Checking dependencies...${NC}"
    missing_deps=()
    
         if ! $PYTHON_CMD -c "import aiohttp" 2>/dev/null; then
         missing_deps+=("aiohttp")
     fi
     
     if ! $PYTHON_CMD -c "import websockets" 2>/dev/null; then
         missing_deps+=("websockets")
     fi
     
     if ! $PYTHON_CMD -c "import firebase_admin" 2>/dev/null; then
         missing_deps+=("firebase-admin")
     fi
     
     if ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
         missing_deps+=("requests")
     fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${YELLOW}⚠️ Installing missing dependencies: ${missing_deps[*]}${NC}"
        pip install "${missing_deps[@]}"
    else
        echo -e "${GREEN}✅ All dependencies are installed${NC}"
    fi
}

# Function to check server health
check_server() {
    print_section "🔍 Server Health Check"
    
    echo -e "${BLUE}Testing connection to: $BASE_URL${NC}"
    
    if curl -s --max-time 10 "$BASE_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is responding at $BASE_URL${NC}"
        
        # Try to get server info
                 server_info=$(curl -s --max-time 5 "$BASE_URL" | $PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', 'Unknown'))" 2>/dev/null || echo "Unable to parse")
        echo -e "${GREEN}📡 Server message: $server_info${NC}"
        
        return 0
    else
        echo -e "${YELLOW}⚠️ Server may not be running at $BASE_URL${NC}"
        echo -e "${YELLOW}   Consider starting the server with: python main.py${NC}"
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}❌ Aborted by user${NC}"
            exit 1
        fi
        
        return 1
    fi
}

# Function to run smoke tests
run_smoke_tests() {
    if [[ "$SKIP_SMOKE" == "true" ]]; then
        echo -e "${YELLOW}⏭️ Skipping smoke tests (--skip-smoke)${NC}"
        return 0
    fi
    
    print_section "🔥 Running Smoke Tests"
    
    smoke_args="--base-url $BASE_URL"
    if [[ "$VERBOSE" == "true" ]]; then
        smoke_args="$smoke_args --verbose"
    fi
    
    echo -e "${BLUE}🚀 Executing smoke tests...${NC}"
    echo -e "${BLUE}Command: python scripts/smoke_test.py $smoke_args${NC}"
    echo ""
    
         if $PYTHON_CMD scripts/smoke_test.py $smoke_args; then
        echo ""
        echo -e "${GREEN}🎉 Smoke tests completed successfully!${NC}"
        return 0
    else
        smoke_exit_code=$?
        echo ""
        if [[ $smoke_exit_code -eq 1 ]]; then
            echo -e "${YELLOW}⚠️ Smoke tests completed with warnings${NC}"
            return 1
        else
            echo -e "${RED}💥 Smoke tests failed${NC}"
            return 2
        fi
    fi
}

# Function to generate documentation
generate_documentation() {
    if [[ "$SKIP_DOCS" == "true" ]]; then
        echo -e "${YELLOW}⏭️ Skipping documentation generation (--skip-docs)${NC}"
        return 0
    fi
    
    print_section "📚 Generating API Documentation"
    
    echo -e "${BLUE}🔧 Generating comprehensive API documentation...${NC}"
    echo -e "${BLUE}Command: python scripts/generate_docs.py --base-url $BASE_URL --output-dir $OUTPUT_DIR${NC}"
    echo ""
    
         if $PYTHON_CMD scripts/generate_docs.py --base-url "$BASE_URL" --output-dir "$OUTPUT_DIR"; then
        echo ""
        echo -e "${GREEN}🎉 Documentation generated successfully!${NC}"
        echo -e "${GREEN}📁 Documentation saved to: $(realpath "$OUTPUT_DIR")${NC}"
        
        # Check if HTML docs exist and offer to open
        html_docs="$OUTPUT_DIR/api_docs.html"
        if [[ -f "$html_docs" ]]; then
            echo -e "${GREEN}🌐 HTML documentation: file://$(realpath "$html_docs")${NC}"
            
            # Offer to open in browser (macOS/Linux)
            if command -v open &> /dev/null; then
                read -p "Open documentation in browser? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    open "file://$(realpath "$html_docs")"
                fi
            elif command -v xdg-open &> /dev/null; then
                read -p "Open documentation in browser? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    xdg-open "file://$(realpath "$html_docs")"
                fi
            fi
        fi
        
        return 0
    else
        echo ""
        echo -e "${RED}💥 Documentation generation failed${NC}"
        return 1
    fi
}

# Function to display summary
display_summary() {
    print_section "📊 Pipeline Summary"
    
    echo -e "${BLUE}🎯 Target API: $BASE_URL${NC}"
    echo -e "${BLUE}📅 Completed at: $(date)${NC}"
    echo ""
    
    if [[ "$SKIP_SMOKE" != "true" ]]; then
        if [[ $smoke_result -eq 0 ]]; then
            echo -e "${GREEN}✅ Smoke Tests: PASSED${NC}"
        elif [[ $smoke_result -eq 1 ]]; then
            echo -e "${YELLOW}⚠️ Smoke Tests: PASSED WITH WARNINGS${NC}"
        else
            echo -e "${RED}❌ Smoke Tests: FAILED${NC}"
        fi
    else
        echo -e "${YELLOW}⏭️ Smoke Tests: SKIPPED${NC}"
    fi
    
    if [[ "$SKIP_DOCS" != "true" ]]; then
        if [[ $docs_result -eq 0 ]]; then
            echo -e "${GREEN}✅ Documentation: GENERATED${NC}"
            echo -e "${GREEN}   📁 Location: $(realpath "$OUTPUT_DIR")${NC}"
        else
            echo -e "${RED}❌ Documentation: FAILED${NC}"
        fi
    else
        echo -e "${YELLOW}⏭️ Documentation: SKIPPED${NC}"
    fi
    
    echo ""
    
    # Overall status
    overall_success=true
    if [[ "$SKIP_SMOKE" != "true" && $smoke_result -gt 1 ]]; then
        overall_success=false
    fi
    if [[ "$SKIP_DOCS" != "true" && $docs_result -ne 0 ]]; then
        overall_success=false
    fi
    
    if [[ "$overall_success" == "true" ]]; then
        echo -e "${GREEN}🎉 Pipeline completed successfully!${NC}"
        
        # Show useful next steps
        echo ""
        echo -e "${CYAN}🚀 Next Steps:${NC}"
        if [[ "$SKIP_DOCS" != "true" && -f "$OUTPUT_DIR/VoiceApp_API.postman_collection.json" ]]; then
            echo -e "${CYAN}   • Import Postman collection: $OUTPUT_DIR/VoiceApp_API.postman_collection.json${NC}"
        fi
        if [[ "$SKIP_DOCS" != "true" && -f "$OUTPUT_DIR/api_docs.html" ]]; then
            echo -e "${CYAN}   • View API docs: file://$(realpath "$OUTPUT_DIR/api_docs.html")${NC}"
        fi
        echo -e "${CYAN}   • Review frontend integration guide: FRONTEND_API_GUIDE.md${NC}"
        echo -e "${CYAN}   • Start developing with the API!${NC}"
        
        return 0
    else
        echo -e "${RED}💥 Pipeline completed with errors${NC}"
        echo -e "${RED}   Please review the failed components above${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${PURPLE}🔥 VoiceApp Complete Test & Documentation Pipeline${NC}"
    echo -e "${PURPLE}===================================================${NC}"
    echo ""
    echo -e "${BLUE}📡 Target API: $BASE_URL${NC}"
    echo -e "${BLUE}📁 Docs Output: $OUTPUT_DIR${NC}"
    echo -e "${BLUE}🔍 Verbose: $VERBOSE${NC}"
    echo ""
    
    # Run all steps
    check_prerequisites
    server_available=$(check_server && echo "true" || echo "false")
    
    # Initialize result variables
    smoke_result=0
    docs_result=0
    
    # Run smoke tests
    if ! run_smoke_tests; then
        smoke_result=$?
    fi
    
    # Generate documentation
    if ! generate_documentation; then
        docs_result=$?
    fi
    
    # Display final summary
    display_summary
}

# Execute main function
main "$@"
exit_code=$?

# Final message
echo ""
if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}🎊 All done! VoiceApp is ready for integration.${NC}"
else
    echo -e "${RED}⚠️ Pipeline completed with issues. Check the logs above.${NC}"
fi

exit $exit_code 