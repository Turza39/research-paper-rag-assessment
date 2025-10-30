"""
MongoDB service for paper storage and retrieval.
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from src.models.paper import Paper, Section

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        """Initialize MongoDB connection."""
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.research_papers
        self.papers = self.db.papers
        self.chunks = self.db.chunks

    async def initialize(self):
        """Initialize database indexes."""
        logger.info("Initializing MongoDB indexes...")
        await self.papers.create_index("title")
        await self.papers.create_index("authors")
        await self.papers.create_index("year")
        await self.chunks.create_index("paper_id")
        await self.chunks.create_index("section")
        await self.chunks.create_index([("vector_id", 1)], unique=True)
        logger.info("MongoDB indexes created successfully")

    async def store_paper(self, paper: Paper) -> str:
        """Store paper metadata in MongoDB."""
        paper_dict = paper.model_dump()
        paper_dict["_id"] = paper_dict.pop("file_path")  # Use file_path as _id
        
        try:
            await self.papers.update_one(
                {"_id": paper_dict["_id"]},
                {"$set": paper_dict},
                upsert=True
            )
            logger.info(f"Stored paper: {paper.title}")
            return paper_dict["_id"]
        except Exception as e:
            logger.error(f"Error storing paper: {str(e)}")
            raise

    async def store_chunk(self, paper_id: str, chunk_text: str, metadata: Dict) -> str:
        """Store a text chunk with its metadata."""
        chunk_doc = {
            "paper_id": paper_id,
            "text": chunk_text,
            "section": metadata.get("section", "unknown"),
            "page": metadata.get("page", 1),
            "vector_id": metadata.get("vector_id"),
            "metadata": metadata,
            "created_at": datetime.utcnow()
        }
        
        try:
            result = await self.chunks.insert_one(chunk_doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing chunk: {str(e)}")
            raise

    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Retrieve paper by ID."""
        paper_doc = await self.papers.find_one({"_id": paper_id})
        if paper_doc:
            return Paper(**paper_doc)
        return None

    async def get_papers(self, paper_ids: List[str] = None) -> List[Paper]:
        """Retrieve multiple papers by IDs."""
        query = {"_id": {"$in": paper_ids}} if paper_ids else {}
        cursor = self.papers.find(query)
        papers = await cursor.to_list(length=None)
        return [Paper(**paper) for paper in papers]

    async def get_paper_chunks(self, paper_id: str) -> List[Dict]:
        """Retrieve all chunks for a paper."""
        cursor = self.chunks.find({"paper_id": paper_id})
        return await cursor.to_list(length=None)

    async def get_chunks_by_vector_ids(self, vector_ids: List[str]) -> List[Dict]:
        """Retrieve chunks by their vector IDs."""
        cursor = self.chunks.find({"vector_id": {"$in": vector_ids}})
        return await cursor.to_list(length=None)