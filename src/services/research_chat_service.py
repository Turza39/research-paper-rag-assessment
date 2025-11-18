"""
MongoDB service for research-specific chat history.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import ASCENDING, DESCENDING
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class ResearchChatService:
    """Service for managing research-specific chat history."""

    def __init__(self, db):
        self.db = db
        self._create_indexes()

    def _create_indexes(self):
        """Create necessary indexes for efficient querying."""
        try:
            # Research chat history indexes
            self.db.research_chat_history.create_index([("research_id", ASCENDING)])
            self.db.research_chat_history.create_index([
                ("research_id", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            self.db.research_chat_history.create_index([("timestamp", DESCENDING)])
            
            logger.info("✅ Research chat history indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {str(e)}")

    async def store_research_chat(
        self,
        research_id: str,
        research_name: str,
        question: str,
        answer: str,
        papers_referenced: List[str],
        citations: List[Dict[str, Any]],
        sources_used: List[str],
        response_time: float,
        confidence: float = 0.0,
        query_type: str = "single-paper",
        difficulty: str = "medium",
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """Store a research chat entry."""
        try:
            chat_entry = {
                "research_id": research_id,
                "research_name": research_name,
                "question": question,
                "answer": answer,
                "papers_referenced": papers_referenced,
                "citations": citations,
                "sources_used": sources_used,
                "response_time": response_time,
                "confidence": confidence,
                "timestamp": datetime.utcnow(),
                "query_type": query_type,
                "difficulty": difficulty,
                "success": success,
                "error_message": error_message,
                "user_rating": None
            }
            
            result = await self.db.research_chat_history.insert_one(chat_entry)
            logger.info(f"✅ Stored research chat for {research_id}: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Error storing research chat: {str(e)}")
            raise

    async def get_research_chat_history(
        self,
        research_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve chat history for a specific research."""
        try:
            cursor = self.db.research_chat_history.find({"research_id": research_id})\
                .sort("timestamp", DESCENDING)\
                .skip(skip)\
                .limit(limit)
            
            entries = []
            async for entry in cursor:
                entry["_id"] = str(entry["_id"])
                # ✅ Convert datetime to ISO string for JSON serialization
                if isinstance(entry.get("timestamp"), datetime):
                    entry["timestamp"] = entry["timestamp"].isoformat()
                entries.append(entry)
            
            logger.info(f"✅ Retrieved {len(entries)} chat entries for {research_id}")
            return entries
        except Exception as e:
            logger.error(f"❌ Error retrieving research chat history: {str(e)}")
            return []

    async def delete_research_chat_history(self, research_id: str) -> int:
        """Delete all chat history for a research topic."""
        try:
            result = await self.db.research_chat_history.delete_many({
                "research_id": research_id
            })
            logger.info(f"✅ Deleted {result.deleted_count} research chat entries for {research_id}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"❌ Error deleting research chat history: {str(e)}")
            raise

    async def get_research_chat_stats(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a research topic's chat history."""
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
                        "all_papers": {"$push": "$papers_referenced"},
                        "all_sources": {"$push": "$sources_used"}
                    }
                }
            ]
            
            result = await self.db.research_chat_history.aggregate(pipeline).to_list(None)
            
            if not result:
                return None
            
            stats = result[0]
            
            # Calculate derived metrics
            success_rate = (stats["successful_queries"] / stats["total_queries"]) \
                if stats["total_queries"] > 0 else 0
            
            # Get unique papers and count references
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

    async def rate_research_chat_entry(self, entry_id: str, rating: int) -> bool:
        """Rate a research chat entry."""
        try:
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
            
            result = await self.db.research_chat_history.update_one(
                {"_id": ObjectId(entry_id)},
                {"$set": {"user_rating": rating}}
            )
            
            logger.info(f"✅ Rated research chat entry {entry_id}: {rating} stars")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Error rating research chat entry: {str(e)}")
            raise

    async def get_research_summary(self, research_id: str) -> Optional[str]:
        """Get a summary of research chat history using Gemini."""
        try:
            # Get recent chat entries
            entries = await self.get_research_chat_history(research_id, limit=5)
            
            if not entries:
                return None
            
            # Build summary text from questions
            questions = [e["question"] for e in entries]
            summary_text = "Recent research questions:\n" + "\n".join(
                [f"- {q}" for q in questions]
            )
            
            # Use Gemini to generate summary
            import os
            import google.generativeai as genai
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("⚠️ GOOGLE_API_KEY not set, skipping Gemini summary")
                return None
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = (
                "Based on these research questions, provide a brief 1-2 sentence summary "
                "of the research focus area:\n\n" + summary_text
            )
            
            response = model.generate_content(prompt)
            summary = response.text.strip() if hasattr(response, "text") else None
            
            logger.info(f"✅ Generated Gemini summary for research {research_id}")
            return summary
        except Exception as e:
            logger.error(f"❌ Error generating research summary: {str(e)}")
            return None