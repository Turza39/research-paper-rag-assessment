#!/bin/bash
# Bash script to start the RAG system

echo "Starting Research Paper RAG System..."

# Create data directory if it doesn't exist
mkdir -p data

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Start Docker services
echo "Starting Docker services..."
docker-compose up --build -d

echo
echo "Services are starting up..."
echo
echo "Access the API documentation at: http://localhost:8000/docs"
echo "MongoDB running on: localhost:27017"
echo "Qdrant running on: localhost:6333"
echo
echo "To stop the services, run: docker-compose down"