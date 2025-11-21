"""
MongoDB service for paper storage, retrieval, and chunk management.
Compatible with simplified Paper schema.
Includes general and research-specific chat history.
"""
from pymongo import ASCENDING, DESCENDING
import logging, os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary
from bson import ObjectId
from src.models.paper import Paper

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

class MongoDBService:
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client.research_papers
        self.papers = self.db.papers
        self.chunks = self.db.chunks
        self.queries = self.db.queries
        self.paper_stats = self.db.paper_stats
        self.query_history = self.db.query_history  # ✅ NEW
        self.research_chat_history = self.db.research_chat_history  # ✅ NEW
        self.researches = self.db.researches  # ✅ RESEARCH TOPICS

    # ================== INITIALIZATION ==================
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

        # Paper stats indexes
        await self.paper_stats.create_index("paper_id", unique=True)

        # ✅ NEW: Query history (for analytics) indexes
        await self.query_history.create_index([("timestamp", DESCENDING)])
        await self.query_history.create_index([("query_type", ASCENDING)])

        # ✅ NEW: Research chat history indexes
        await self.research_chat_history.create_index([("research_id", ASCENDING)])
        await self.research_chat_history.create_index([
            ("research_id", ASCENDING),
            ("timestamp", DESCENDING)
        ])
        await self.research_chat_history.create_index([("timestamp", DESCENDING)])

        # ✅ NEW: Research topics indexes
        await self.researches.create_index([("_id", ASCENDING)])
        await self.researches.create_index([("created_at", DESCENDING)])
        await self.researches.create_index([("name", 1)])
        await self.researches.create_index([("tags", 1)])
        await self.researches.create_index([("is_archived", ASCENDING)])

        logger.info("✅ MongoDB indexes created successfully.")

    # ================== PAPER METHODS ==================
    async def paper_exists(self, file_name: str) -> bool:
        """Check if a paper with the same file_name already exists."""
        paper_doc = await self.papers.find_one({"file_name": file_name})
        return paper_doc is not None

    async def store_paper(
        self,
        paper: Paper,
        pdf_bytes: Optional[bytes] = None,
        metadata_embedding: Optional[list] = None
    ) -> str:
        """Store a paper with its metadata and optional PDF."""
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
        """Retrieve a specific paper by ID."""
        paper_doc = await self.papers.find_one({"_id": paper_id})
        if paper_doc:
            return Paper(**paper_doc)
        return None

    async def get_papers(self, paper_ids: List[str] = None) -> List[Paper]:
        """Retrieve all papers or specific papers by IDs."""
        query = {"_id": {"$in": paper_ids}} if paper_ids else {}
        cursor = self.papers.find(query)
        papers = await cursor.to_list(length=None)
        return [Paper(**paper) for paper in papers]

    # ================== CHUNK METHODS ==================
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
        """Retrieve all chunks for a paper."""
        cursor = self.chunks.find({"paper_id": paper_id})
        return await cursor.to_list(length=None)

    async def get_chunks_by_vector_ids(self, vector_ids: List[str]) -> List[Dict]:
        """Retrieve chunks by their vector IDs."""
        cursor = self.chunks.find({"vector_id": {"$in": vector_ids}})
        return await cursor.to_list(length=None)

    # ================== QUERY HISTORY (Analytics) ==================
    async def store_query(self, query_history: Dict) -> str:
        """Store a query in the analytics query history collection."""
        query_history["timestamp"] = datetime.now(timezone.utc)
        try:
            result = await self.queries.insert_one(query_history)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing query history: {str(e)}")
            raise

    async def get_query_history(self, limit: int = 50) -> List[Dict]:
        """Retrieve query history for analytics."""
        cursor = self.queries.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=None)

    # ================== PAPER STATS ==================
    async def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper and all associated chunks and stats."""
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
        """Get statistics for a paper."""
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
        """Update statistics for a paper after a query."""
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

    # ================== ANALYTICS / POPULAR TOPICS ==================
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
                    "_id": "$question",
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

    # ================== GENERAL CHAT HISTORY ==================

    async def store_general_chat_entry(
        self,
        question: str,
        answer: str,
        response_time: float,
        papers_referenced: List[str],
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store general chat entry in query_history collection."""
        try:
            query_entry = {
                "question": question,
                "answer": answer,
                "response_time": response_time,
                "papers_referenced": papers_referenced,
                "timestamp": datetime.now(timezone.utc),
                "query_type": "general",
                "difficulty": "medium",
                "success": True,
                "user_rating": None
            }
            # Merge metadata if provided
            if metadata:
                query_entry.update(metadata)
            
            result = await self.query_history.insert_one(query_entry)
            logger.info(f"✅ Stored general chat entry: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Error storing general chat entry: {str(e)}")
            raise

    async def get_general_chat_history(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve general chat history from query_history collection."""
        try:
            cursor = self.query_history.find()\
                .sort("timestamp", DESCENDING)\
                .skip(skip)\
                .limit(limit)
            
            entries = []
            async for entry in cursor:
                entry["_id"] = str(entry["_id"])
                if isinstance(entry.get("timestamp"), datetime):
                    entry["timestamp"] = entry["timestamp"].isoformat()
                entries.append(entry)
            
            logger.info(f"✅ Retrieved {len(entries)} general chat entries")
            return entries
        except Exception as e:
            logger.error(f"❌ Error retrieving general chat history: {str(e)}")
            return []

    async def delete_general_chat_history(self) -> int:
        """Delete all general chat history."""
        try:
            result = await self.query_history.delete_many({})
            logger.info(f"✅ Deleted {result.deleted_count} general chat entries")
            return result.deleted_count
        except Exception as e:
            logger.error(f"❌ Error deleting general chat history: {str(e)}")
            raise

    # ================== RESEARCH CHAT HISTORY ==================

    async def store_research_chat_entry(
        self,
        research_id: str,
        research_name: str,
        question: str,
        answer: str,
        papers_referenced: List[str],
        citations: List[Dict[str, Any]],
        sources_used: List[str],
        response_time: float = 0.0,
        confidence: float = 0.0,
        query_type: str = "single-paper",
        difficulty: str = "medium",
        success: bool = True,
        error_message: Optional[str] = None,
        context_score: float = 0.0,
        context_level: str = "medium",
        detected_section: Optional[str] = None,
        is_out_of_context: bool = False,
        clarification_needed: bool = False,
        retrieval_count: int = 0,
        response_time_ms: Optional[float] = None,
        **kwargs
    ) -> str:
        """Store research chat entry in research_chat_history collection."""
        try:
            # Convert response_time_ms to seconds if provided
            if response_time_ms is not None and response_time == 0.0:
                response_time = response_time_ms / 1000.0
            
            chat_entry = {
                "research_id": research_id,
                "research_name": research_name,
                "question": question,
                "answer": answer,
                "papers_referenced": papers_referenced,
                "citations": citations,
                "sources_used": sources_used,
                "response_time": response_time,
                "response_time_ms": response_time_ms,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc),
                "query_type": query_type,
                "difficulty": difficulty,
                "success": success,
                "error_message": error_message,
                "user_rating": None,
                "context_score": context_score,
                "context_level": context_level,
                "detected_section": detected_section,
                "is_out_of_context": is_out_of_context,
                "clarification_needed": clarification_needed,
                "retrieval_count": retrieval_count
            }
            # Accept any additional kwargs and merge them
            for key, value in kwargs.items():
                if key not in chat_entry:
                    chat_entry[key] = value
            
            result = await self.research_chat_history.insert_one(chat_entry)
            logger.info(f"✅ Stored research chat entry: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Error storing research chat entry: {str(e)}")
            raise

    async def get_research_chat_history(
        self,
        research_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve research chat history from research_chat_history collection."""
        try:
            cursor = self.research_chat_history.find({"research_id": research_id})\
                .sort("timestamp", DESCENDING)\
                .skip(skip)\
                .limit(limit)
            
            entries = []
            async for entry in cursor:
                entry["_id"] = str(entry["_id"])
                if isinstance(entry.get("timestamp"), datetime):
                    entry["timestamp"] = entry["timestamp"].isoformat()
                entries.append(entry)
            
            logger.info(f"✅ Retrieved {len(entries)} research chat entries for {research_id}")
            return entries
        except Exception as e:
            logger.error(f"❌ Error retrieving research chat history: {str(e)}")
            return []

    async def delete_research_chat_history(self, research_id: str) -> int:
        """Delete all chat history for a research topic."""
        try:
            result = await self.research_chat_history.delete_many({
                "research_id": research_id
            })
            logger.info(f"✅ Deleted {result.deleted_count} research chat entries")
            return result.deleted_count
        except Exception as e:
            logger.error(f"❌ Error deleting research chat history: {str(e)}")
            raise

    async def get_research_chat_stats(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for research chat history."""
        try:
            pipeline = [
                {"$match": {"research_id": research_id}},
                {
                    "$group": {
                        "_id": "$research_id",
                        "research_name": {"$first": "$research_name"},
                        "total_queries": {"$sum": 1},
                        "successful_queries": {
                            "$sum": {"$cond": ["$success", 1, 0]}
                        },
                        "failed_queries": {
                            "$sum": {"$cond": ["$success", 0, 1]}
                        },
                        "avg_response_time": {"$avg": "$response_time"},
                        "avg_confidence": {"$avg": "$confidence"},
                        "last_query_time": {"$max": "$timestamp"},
                        "all_papers": {"$push": "$papers_referenced"}
                    }
                }
            ]
            
            result = await self.research_chat_history.aggregate(pipeline).to_list(None)
            
            if not result:
                return None
            
            stats = result[0]
            success_rate = (stats["successful_queries"] / stats["total_queries"]) \
                if stats["total_queries"] > 0 else 0
            
            all_papers_flat = [p for papers in stats["all_papers"] for p in papers]
            paper_counts = {}
            for paper in all_papers_flat:
                paper_counts[paper] = paper_counts.get(paper, 0) + 1
            
            unique_papers = list(paper_counts.keys())
            most_referenced = sorted(
                [{"paper": p, "count": c} for p, c in paper_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:5]
            
            return {
                "research_id": research_id,
                "research_name": stats.get("research_name", "Untitled"),
                "total_queries": stats["total_queries"],
                "successful_queries": stats["successful_queries"],
                "failed_queries": stats["failed_queries"],
                "success_rate": round(success_rate, 2),
                "avg_response_time": round(stats.get("avg_response_time", 0), 2),
                "avg_confidence": round(stats.get("avg_confidence", 0), 2),
                "total_papers_referenced": len(all_papers_flat),
                "unique_papers": unique_papers,
                "last_query_time": stats.get("last_query_time"),
                "most_referenced_papers": most_referenced
            }
        except Exception as e:
            logger.error(f"❌ Error getting research chat stats: {str(e)}")
            return None

    # ================== RESEARCH TOPIC MANAGEMENT ==================

    async def create_research(
        self,
        name: str,
        description: Optional[str] = None,
        papers: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Create a new research topic."""
        try:
            research_doc = {
                "name": name,
                "description": description or "",
                "papers": papers or [],
                "tags": tags or [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_archived": False
            }

            result = await self.researches.insert_one(research_doc)
            logger.info(f"✅ Created research topic: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Error creating research: {str(e)}")
            raise

    async def get_research(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific research topic by ID."""
        try:
            research_doc = await self.researches.find_one({"_id": ObjectId(research_id)})
            if research_doc:
                research_doc["_id"] = str(research_doc["_id"])
                if isinstance(research_doc.get("created_at"), datetime):
                    research_doc["created_at"] = research_doc["created_at"].isoformat()
                if isinstance(research_doc.get("updated_at"), datetime):
                    research_doc["updated_at"] = research_doc["updated_at"].isoformat()
                return research_doc
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving research: {str(e)}")
            return None

    async def get_all_researches(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Retrieve all research topics."""
        try:
            query = {} if include_archived else {"is_archived": False}
            cursor = self.researches.find(query).sort("created_at", DESCENDING)
            researches = []

            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                if isinstance(doc.get("updated_at"), datetime):
                    doc["updated_at"] = doc["updated_at"].isoformat()
                researches.append(doc)

            logger.info(f"✅ Retrieved {len(researches)} research topics")
            return researches
        except Exception as e:
            logger.error(f"❌ Error retrieving researches: {str(e)}")
            return []

    async def update_research(
        self,
        research_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        papers: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        is_archived: Optional[bool] = None
    ) -> bool:
        """Update a research topic."""
        try:
            update_data = {}

            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if papers is not None:
                update_data["papers"] = papers
            if tags is not None:
                update_data["tags"] = tags
            if is_archived is not None:
                update_data["is_archived"] = is_archived

            update_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.researches.update_one(
                {"_id": ObjectId(research_id)},
                {"$set": update_data}
            )

            if result.matched_count > 0:
                logger.info(f"✅ Updated research topic: {research_id}")
                return True
            else:
                logger.warning(f"⚠️ Research topic not found: {research_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Error updating research: {str(e)}")
            raise

    async def add_paper_to_research(self, research_id: str, paper_id: str) -> bool:
        """Add a paper to a research topic."""
        try:
            result = await self.researches.update_one(
                {"_id": ObjectId(research_id)},
                {
                    "$addToSet": {"papers": paper_id},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )

            if result.matched_count > 0:
                logger.info(f"✅ Added paper {paper_id} to research {research_id}")
                return True
            else:
                logger.warning(f"⚠️ Research topic not found: {research_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Error adding paper to research: {str(e)}")
            raise

    async def remove_paper_from_research(self, research_id: str, paper_id: str) -> bool:
        """Remove a paper from a research topic."""
        try:
            result = await self.researches.update_one(
                {"_id": ObjectId(research_id)},
                {
                    "$pull": {"papers": paper_id},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )

            if result.matched_count > 0:
                logger.info(f"✅ Removed paper {paper_id} from research {research_id}")
                return True
            else:
                logger.warning(f"⚠️ Research topic not found: {research_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Error removing paper from research: {str(e)}")
            raise

    async def delete_research(self, research_id: str) -> bool:
        """Delete a research topic and its chat history."""
        try:
            # Delete research topic
            result = await self.researches.delete_one({"_id": ObjectId(research_id)})

            if result.deleted_count > 0:
                # Also delete associated chat history
                await self.research_chat_history.delete_many({"research_id": research_id})
                logger.info(f"✅ Deleted research topic: {research_id}")
                return True
            else:
                logger.warning(f"⚠️ Research topic not found: {research_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Error deleting research: {str(e)}")
            raise


# ================== SINGLETON INSTANCE ==================

mongodb_instance = MongoDBService()


async def get_mongodb() -> MongoDBService:
    """Get MongoDB service instance."""
    return mongodb_instance