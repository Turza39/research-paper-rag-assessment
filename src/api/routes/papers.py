from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import logging

from src.services.mongodb_service import MongoDBService, get_mongodb
from src.services.pdf_processor import PDFProcessor
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore
from src.models.paper import Paper
from src.models.history import PaperStats

logger = logging.getLogger(__name__)
router = APIRouter()


# ----------------- Upload Paper -----------------
@router.post("/papers/upload", response_model=Paper)
async def upload_paper(
    file: UploadFile = File(...),
    mongodb: MongoDBService = Depends(get_mongodb)
):
    try:
        file_name = file.filename

        # Check if paper already exists
        if await mongodb.paper_exists(file_name):
            raise HTTPException(status_code=400, detail="Paper already exists")

        # Read PDF bytes in memory
        pdf_bytes = await file.read()
        pdf_processor = PDFProcessor()
        text, metadata = pdf_processor.extract_text_from_bytes(pdf_bytes)

        # ✅ Create chunks with UUID-based vector IDs
        chunks = pdf_processor.create_chunks(
            text,
            {**metadata, "file_name": file_name}  # ensure 'file_name' is present
        )

        # Build Paper object
        paper = Paper(
            id=file_name,
            file_name=file_name,
            page_count=metadata.get("page_count", 0),
            vector_count=len(chunks),
            metadata={
                "title": metadata.get("title", file_name),
                "initial_content": text[:500],
                "file_name": file_name
            }
        )

        # Store paper info in MongoDB
        paper_id = await mongodb.store_paper(paper, pdf_bytes=pdf_bytes)

        if chunks:
            # Initialize embedding service
            embedding_service = EmbeddingService()
            vectors = embedding_service.get_embeddings(chunks)

            # ✅ Keep the same UUIDs for MongoDB and Qdrant
            chunk_docs = [
                {
                    "text": c.text,
                    "metadata": c.metadata,
                    "vector_id": c.metadata["vector_id"],  # use UUID from chunk
                }
                for c in chunks
            ]

            # Store chunks in MongoDB
            await mongodb.store_chunks_bulk(paper_id, chunk_docs)

            # Initialize vector store
            vector_store = VectorStore()
            vector_store.store_vectors(chunks, vectors)

        logger.info(f"✅ Uploaded and processed paper: {file_name}")
        return paper

    except Exception as e:
        logger.error(f"Error uploading paper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- List Papers -----------------
@router.get("/papers", response_model=List[Paper])
async def list_papers(
    mongodb: MongoDBService = Depends(get_mongodb),
    skip: int = 0,
    limit: int = 20
):
    try:
        papers = await mongodb.get_papers()
        return papers[skip:skip + limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Get Paper -----------------
@router.get("/papers/{paper_id}", response_model=Paper)
async def get_paper(
    paper_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    paper = await mongodb.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


# ----------------- Delete Paper -----------------
@router.delete("/papers/{paper_id}")
async def delete_paper(
    paper_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    try:
        success = await mongodb.delete_paper(paper_id)
        if not success:
            raise HTTPException(status_code=404, detail="Paper not found")
        return {"message": "Paper deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Get Paper Stats -----------------
@router.get("/papers/{paper_id}/stats", response_model=PaperStats)
async def get_paper_stats(
    paper_id: str,
    mongodb: MongoDBService = Depends(get_mongodb)
):
    try:
        stats = await mongodb.get_paper_stats(paper_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Paper stats not found")
        return PaperStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
