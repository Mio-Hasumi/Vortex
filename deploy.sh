#!/bin/bash

# VoiceApp Backend Deployment Script
# This script helps you quickly test the Docker deployment

set -e

echo "🚀 VoiceApp Backend Deployment Script"
echo "======================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "📋 Checking dependencies..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if Firebase credentials exist
if [ ! -f "voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json" ]; then
    echo "❌ Firebase credentials file not found!"
    echo "   Please ensure 'voiceapp-8f09a-firebase-adminsdk-fbsvc-4f84f483d1.json' exists in the current directory"
    exit 1
fi

echo "✅ Firebase credentials file found"

# Ask user for deployment type
echo ""
echo "🎯 Select deployment type:"
echo "1) Development (with hot reload)"
echo "2) Production (with nginx)"
echo "3) Simple (app + redis only)"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo "🛠️  Starting development environment..."
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.dev.yml up --build -d
        COMPOSE_FILE="docker-compose.dev.yml"
        ;;
    2)
        echo "🚀 Starting production environment..."
        docker-compose down
        docker-compose up --build -d
        COMPOSE_FILE="docker-compose.yml"
        ;;
    3)
        echo "🔧 Starting simple environment..."
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.dev.yml up --build -d app redis
        COMPOSE_FILE="docker-compose.dev.yml"
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Backend is healthy!"
else
    echo "⚠️  Backend health check failed. Check logs with:"
    echo "   docker-compose -f $COMPOSE_FILE logs app"
fi

# Redis check
echo "🔍 Checking Redis connection..."
if docker exec $(docker-compose -f $COMPOSE_FILE ps -q redis) redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis is running!"
else
    echo "⚠️  Redis connection failed. Check logs with:"
    echo "   docker-compose -f $COMPOSE_FILE logs redis"
fi

echo ""
echo "🎉 Deployment completed!"
echo "======================================"
echo "🌐 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo "📦 Redis: localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "   Stop services: docker-compose -f $COMPOSE_FILE down"
echo "   Restart: docker-compose -f $COMPOSE_FILE restart"
echo ""
echo "🎯 Test your API at: http://localhost:8000/docs" 