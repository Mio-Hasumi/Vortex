#!/bin/bash

# VoiceApp Docker-based Testing
# =============================

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
RUN_SMOKE=true
RUN_DOCS=true
CLEANUP=true
DETACH=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-smoke)
      RUN_SMOKE=false
      shift
      ;;
    --skip-docs)
      RUN_DOCS=false
      shift
      ;;
    --no-cleanup)
      CLEANUP=false
      shift
      ;;
    --detach|-d)
      DETACH=true
      shift
      ;;
    --help|-h)
      echo -e "${CYAN}VoiceApp Docker-based Testing${NC}"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --skip-smoke     Skip smoke tests"
      echo "  --skip-docs      Skip documentation generation"
      echo "  --no-cleanup     Don't cleanup containers after completion"
      echo "  --detach, -d     Run containers in detached mode"
      echo "  --help, -h       Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Run full test suite"
      echo "  $0 --skip-docs        # Only run smoke tests"
      echo "  $0 --detach           # Run in background"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${PURPLE}🐳 VoiceApp Docker-based Testing${NC}"
echo -e "${PURPLE}================================${NC}"
echo ""

# Function to cleanup
cleanup() {
    if [[ "$CLEANUP" == "true" ]]; then
        echo -e "${BLUE}🧹 Cleaning up Docker containers...${NC}"
        docker-compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true
        echo -e "${GREEN}✅ Cleanup completed${NC}"
    else
        echo -e "${YELLOW}⚠️ Skipping cleanup (--no-cleanup specified)${NC}"
    fi
}

# Set cleanup trap
trap cleanup EXIT

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed. Please install it and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is available${NC}"

# Build images
echo -e "${BLUE}🔨 Building Docker images...${NC}"
if docker-compose -f docker-compose.test.yml build; then
    echo -e "${GREEN}✅ Images built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build images${NC}"
    exit 1
fi

# Start infrastructure services
echo -e "${BLUE}🚀 Starting infrastructure services...${NC}"
if docker-compose -f docker-compose.test.yml up -d redis voiceapp-api; then
    echo -e "${GREEN}✅ Infrastructure services started${NC}"
else
    echo -e "${RED}❌ Failed to start infrastructure services${NC}"
    exit 1
fi

# Wait for API to be healthy
echo -e "${BLUE}⏳ Waiting for API to be healthy...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f docker-compose.test.yml exec -T voiceapp-api curl -f http://localhost:8000/ >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API is healthy and ready${NC}"
        break
    fi
    
    ((attempt++))
    echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - waiting for API...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ API failed to become healthy within timeout${NC}"
    docker-compose -f docker-compose.test.yml logs voiceapp-api
    exit 1
fi

# Run smoke tests
if [[ "$RUN_SMOKE" == "true" ]]; then
    echo -e "${BLUE}🔥 Running smoke tests...${NC}"
    
    if [[ "$DETACH" == "true" ]]; then
        docker-compose -f docker-compose.test.yml up -d smoke-tests
        echo -e "${YELLOW}⚠️ Smoke tests running in background${NC}"
    else
        if docker-compose -f docker-compose.test.yml run --rm smoke-tests; then
            echo -e "${GREEN}✅ Smoke tests passed${NC}"
        else
            echo -e "${RED}❌ Smoke tests failed${NC}"
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}⏭️ Skipping smoke tests${NC}"
fi

# Generate documentation
if [[ "$RUN_DOCS" == "true" ]]; then
    echo -e "${BLUE}📚 Generating documentation...${NC}"
    
    if [[ "$DETACH" == "true" ]]; then
        docker-compose -f docker-compose.test.yml up -d docs-generator
        echo -e "${YELLOW}⚠️ Documentation generation running in background${NC}"
    else
        if docker-compose -f docker-compose.test.yml run --rm docs-generator; then
            echo -e "${GREEN}✅ Documentation generated successfully${NC}"
            
            # Show generated files
            echo -e "${BLUE}📁 Generated documentation files:${NC}"
            ls -la docs/ 2>/dev/null || echo "  (No documentation files found)"
        else
            echo -e "${RED}❌ Documentation generation failed${NC}"
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}⏭️ Skipping documentation generation${NC}"
fi

# Show logs if detached
if [[ "$DETACH" == "true" ]]; then
    echo ""
    echo -e "${CYAN}📋 Container Status:${NC}"
    docker-compose -f docker-compose.test.yml ps
    
    echo ""
    echo -e "${CYAN}🔍 To view logs:${NC}"
    echo "  docker-compose -f docker-compose.test.yml logs smoke-tests"
    echo "  docker-compose -f docker-compose.test.yml logs docs-generator"
    echo "  docker-compose -f docker-compose.test.yml logs voiceapp-api"
    
    echo ""
    echo -e "${CYAN}🛑 To stop services:${NC}"
    echo "  docker-compose -f docker-compose.test.yml down"
fi

echo ""
echo -e "${GREEN}🎉 Docker-based testing completed successfully!${NC}" 