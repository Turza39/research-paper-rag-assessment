"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
from src.services.rag_pipeline import RAGPipeline

# ----------------- Lifespan -----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup and teardown logic for FastAPI."""
    print("🔄 Checking and processing existing PDFs...")

    pipeline = RAGPipeline()
    sample_papers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_papers")

    if os.path.exists(sample_papers_dir):
        print(f"📁 Found sample papers at {sample_papers_dir}, processing...")
        pipeline.process_directory(sample_papers_dir)
    else:
        print(f"⚠️ Skipping initialization — directory not found: {sample_papers_dir}")

    yield  # Application runs after this line

    # 🔚 Teardown (optional)
    print("🧹 Shutting down... cleanup complete.")


# ----------------- FastAPI App -----------------
app = FastAPI(
    title="Research Paper RAG System",
    description="""
    Research Paper RAG System API

    This API provides intelligent query capabilities across research papers using RAG (Retrieval Augmented Generation).
    """,
    version="1.0.0",
    lifespan=lifespan
)

# ----------------- Include Routers -----------------
from src.api.routes.query import router as query_router
from src.api.routes.analytics import router as history_router
from src.api.routes.papers import router as papers_router

app.include_router(query_router, prefix="/api/v1", tags=["query"])
app.include_router(history_router, prefix="/api/v1", tags=["history"])
app.include_router(papers_router, prefix="/api/v1", tags=["papers"])
