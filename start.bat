@echo off
REM Windows batch script to start the RAG system

echo Starting Research Paper RAG System...

REM Create data directory if it doesn't exist
if not exist "data" mkdir data

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
)

REM Start Docker services
echo Starting Docker services...
docker-compose up --build -d

echo.
echo Services are starting up...
echo.
echo Access the API documentation at: http://localhost:8000/docs
echo MongoDB running on: localhost:27017
echo Qdrant running on: localhost:6333
echo.
echo To stop the services, run: docker-compose down