"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI

app = FastAPI(title="Research Paper RAG System")

# Import routes
from src.api.routes import router as api_router

# Include routes
app.include_router(api_router, prefix="/api")