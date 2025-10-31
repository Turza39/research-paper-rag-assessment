"""
MongoDB service for paper storage, retrieval, and chunk management.
Compatible with simplified Paper schema.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary
from src.models.paper import Paper

logger = logging.getLogger(__name__)



class MongoDBService:
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        """Initialize MongoDB connection."""
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.research_papers
        self.papers = self.db.papers
        self.chunks = self.db.chunks
        self.queries = self.db.queries
        self.paper_stats = self.db.paper_stats

    # ---------------- Initialization ----------------
    async def initialize(self):
        """Initialize MongoDB indexes for performance."""
        logger.info("Initializing MongoDB indexes...")

        # Paper indexes
        await self.papers.create_index("file_name", unique=True)
        await self.papers.create_index([("metadata_embedding", "text")])

        # Chunk indexes
        await self.chunks.create_index("paper_id")
        await self.chunks.create_index("section")
        await self.chunks.create_index("page")
        await self.chunks.create_index([("vector_id", 1)], unique=True)

        # Query history indexes
        await self.queries.create_index("timestamp")
        await self.queries.create_index("papers_referenced")
        await self.queries.create_index("query_type")

        # Paper stats
        await self.paper_stats.create_index("paper_id", unique=True)

        logger.info("✅ MongoDB indexes created successfully.")

    # ---------------- Paper Methods ----------------
    async def paper_exists(self, file_name: str) -> bool:
        """Check if a paper with the same file_name already exists."""
        paper_doc = await self.papers.find_one({"file_name": file_name})
        return paper_doc is not None

    async def store_paper(self, paper: Paper, pdf_bytes: Optional[bytes] = None, metadata_embedding: Optional[list] = None) -> str:
        paper_dict = paper.model_dump()
        paper_dict["_id"] = paper.id  # file_name as _id

        if pdf_bytes:
            paper_dict["pdf_file"] = Binary(pdf_bytes)

        if metadata_embedding:
            paper_dict["metadata_embedding"] = metadata_embedding

        paper_dict["created_at"] = datetime.now(timezone.utc)

        await self.papers.update_one(
            {"_id": paper_dict["_id"]},
            {"$set": paper_dict},
            upsert=True
        )
        return paper_dict["_id"]

    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        paper_doc = await self.papers.find_one({"_id": paper_id})
        if paper_doc:
            return Paper(**paper_doc)
        return None

    async def get_papers(self, paper_ids: List[str] = None) -> List[Paper]:
        query = {"_id": {"$in": paper_ids}} if paper_ids else {}
        cursor = self.papers.find(query)
        papers = await cursor.to_list(length=None)
        return [Paper(**paper) for paper in papers]

    # ---------------- Chunk Methods ----------------
    async def store_chunk(self, paper_id: str, chunk_text: str, metadata: Dict) -> str:
        """Store a single text chunk and its metadata."""
        chunk_doc = {
            "paper_id": paper_id,
            "text": chunk_text,
            "section": metadata.get("section", "unknown"),
            "page": metadata.get("page", 1),
            "vector_id": metadata.get("vector_id"),
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc)
        }

        try:
            result = await self.chunks.insert_one(chunk_doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing chunk: {str(e)}")
            raise

    async def store_chunks_bulk(self, paper_id: str, chunks: List[Dict]) -> List[str]:
        """Store multiple chunks efficiently."""
        for chunk in chunks:
            chunk["paper_id"] = paper_id
            chunk["created_at"] = datetime.now(timezone.utc)

        try:
            result = await self.chunks.insert_many(chunks)
            return [str(_id) for _id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error storing chunks in bulk: {str(e)}")
            raise

    async def get_paper_chunks(self, paper_id: str) -> List[Dict]:
        cursor = self.chunks.find({"paper_id": paper_id})
        return await cursor.to_list(length=None)

    async def get_chunks_by_vector_ids(self, vector_ids: List[str]) -> List[Dict]:
        cursor = self.chunks.find({"vector_id": {"$in": vector_ids}})
        return await cursor.to_list(length=None)

    # ---------------- Query History ----------------
    async def store_query(self, query_history: Dict) -> str:
        query_history["timestamp"] = datetime.now(timezone.utc)
        try:
            result = await self.queries.insert_one(query_history)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing query history: {str(e)}")
            raise

    async def get_query_history(self, limit: int = 50) -> List[Dict]:
        cursor = self.queries.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=None)

    # ---------------- Paper Stats ----------------
    async def delete_paper(self, paper_id: str) -> bool:
        try:
            paper_result = await self.papers.delete_one({"_id": paper_id})
            chunks_result = await self.chunks.delete_many({"paper_id": paper_id})
            await self.paper_stats.delete_one({"paper_id": paper_id})
            logger.info(f"Deleted paper {paper_id} with {chunks_result.deleted_count} chunks")
            return paper_result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting paper: {str(e)}")
            raise

    async def get_paper_stats(self, paper_id: str) -> Dict:
        stats = await self.paper_stats.find_one({"paper_id": paper_id}) or {}
        recent_queries = await self.queries.find(
            {"papers_referenced": paper_id}
        ).sort("timestamp", -1).limit(5).to_list(length=None)

        return {
            "total_queries": stats.get("total_queries", 0),
            "avg_relevance_score": stats.get("avg_relevance_score", 0.0),
            "total_citations": stats.get("total_citations", 0),
            "last_queried": stats.get("last_queried", None),
        }

    async def update_paper_stats(self, paper_id: str, query_data: Dict):
        update = {
            "$inc": {
                "total_queries": 1,
                "total_citations": len(query_data.get("citations", [])),
            },
            "$set": {
                "last_queried": datetime.now(timezone.utc)
            },
        }

        await self.paper_stats.update_one(
            {"paper_id": paper_id},
            update,
            upsert=True
        )

    # ---------------- Analytics / Popular Topics ----------------
    async def get_popular_topics(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Return the most queried topics in the last `days` days.
        Aggregates by question text, with average response time and success rate.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {
                "$group": {
                    "_id": "$question",  # use the correct field
                    "query_count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time"},
                    "success_rate": {"$avg": {"$cond": ["$success", 1, 0]}},
                    "last_queried": {"$max": "$timestamp"}
                }
            },
            {"$sort": {"query_count": -1}},
            {"$limit": limit}
        ]

        cursor = self.queries.aggregate(pipeline)
        results = []

        async for doc in cursor:
            results.append({
                "topic": doc["_id"] if doc["_id"] is not None else "unknown",
                "query_count": doc.get("query_count", 0),
                "avg_response_time": doc.get("avg_response_time", 0.0),
                "success_rate": doc.get("success_rate", 0.0),
                "last_queried": doc.get("last_queried", datetime.now(timezone.utc))
            })

        return results

mongodb_instance = MongoDBService()

async def get_mongodb() -> MongoDBService:
    return mongodb_instance
