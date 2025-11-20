"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ----------------- Lifespan -----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup and teardown logic for FastAPI."""
    print("✅ Application initialized. Ready to accept uploaded PDFs.")
    print("📌 Note: This system now accepts uploaded PDFs only.")
    print("   Use POST /api/v1/papers/upload to add research papers.")

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

# ----------------- ADD CORS MIDDLEWARE -----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Include Routers -----------------
from src.api.routes.query import router as query_router
from src.api.routes.analytics import router as history_router
from src.api.routes.papers import router as papers_router
from src.api.routes.research_chat import router as research_chat_router
from src.api.routes.research import router as research_router

app.include_router(papers_router, prefix="/api/v1", tags=["papers"])
app.include_router(query_router, prefix="/api/v1", tags=["query"])
app.include_router(research_chat_router, prefix="/api/v1", tags=["research_chat"])
app.include_router(research_router, prefix="/api/v1", tags=["research"])
