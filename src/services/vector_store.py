"""
Service for managing vector storage using Qdrant.
Requires Qdrant running in Docker: docker run -p 6333:6333 qdrant/qdrant
"""
import logging
from qdrant_client.http import models as qmodels
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from src.models.paper import Chunk, Section
import uuid, os

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, collection_name: str = "research_papers", host: str = "localhost", port: int = 6333):
        """
        Initialize Qdrant client.
        :param collection_name: Name of the collection to store vectors
        :param host: Qdrant host (Docker)
        :param port: Qdrant port (Docker)
        """
        QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
        QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

        self.client = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")

        self.collection_name = collection_name
        self._init_collection()

    def _init_collection(self, vector_size: int = 384):
        """Create collection if it does not exist."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            logger.info(f"✅ Created collection: {self.collection_name}")
        else:
            logger.info(f"📦 Collection already exists: {self.collection_name}")

    def store_vectors(self, chunks: List[Chunk], vectors: List[List[float]]) -> List[str]:
        """Store chunks and their vector embeddings into Qdrant."""
        if not chunks or not vectors:
            logger.warning("No chunks or vectors provided to store")
            return []

        vector_ids = []
        batch_size = 100

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_vectors = vectors[i:i + batch_size]
            points = []

            for chunk, vector in zip(batch_chunks, batch_vectors):
                point_id = chunk.metadata.get("vector_id")
                if not point_id:
                    point_id = str(uuid.uuid4())
                    chunk.metadata["vector_id"] = point_id

                vector_ids.append(point_id)

                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": chunk.text,
                        **chunk.metadata
                    }
                ))

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"✅ Stored batch of {len(points)} vectors successfully")
            except Exception as e:
                logger.error(f"❌ Error storing vectors: {str(e)}")
                raise

        return vector_ids

    def search_similar(
        self,
        query_vector: List[float],
        paper_filter: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Qdrant with optional paper filtering.
        """
        logger.info(f"🔍 Starting vector search | limit={limit} | filter={paper_filter}")

        query_filter = None
        if paper_filter:
            query_filter = qmodels.Filter(
                should=[
                    qmodels.FieldCondition(
                        key="file_name",
                        match=qmodels.MatchValue(value=paper_name)
                    )
                    for paper_name in paper_filter
                ] + [
                    qmodels.FieldCondition(
                        key="source",
                        match=qmodels.MatchValue(value=paper_name)
                    )
                    for paper_name in paper_filter
                ]
            )
            logger.info(f"📁 Using flexible filter on both file_name & source: {paper_filter}")
        
        try:
            # ✅ FIXED: Use query_points() instead of search()
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit
            ).points  # ✅ Access .points attribute
            
            logger.info(f"✅ Qdrant returned {len(results)} hits")
        except Exception as e:
            logger.error(f"❌ Qdrant search failed: {e}", exc_info=True)
            return []

        formatted_results = []
        for i, hit in enumerate(results):
            text = hit.payload.get("text", "")[:80].replace("\n", " ")
            logger.debug(f"Result {i+1}: score={hit.score:.4f} | snippet='{text}...'")
            formatted_results.append({
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                "score": hit.score
            })

        return formatted_results