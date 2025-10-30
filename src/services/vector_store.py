"""
Service for managing vector storage using Qdrant.
Requires Qdrant running in Docker: docker run -p 6333:6333 qdrant/qdrant
"""
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from src.models.paper import Chunk, Section
import uuid


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
        self.client = QdrantClient(host=host, port=port)
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


    def store_vectors(self, chunks: List[Chunk], vectors: List[List[float]]) -> List[str]:
        """
        Store chunks and their vector embeddings into Qdrant.
        :param chunks: List of Chunk objects with text and metadata
        :param vectors: List of corresponding vector embeddings
        :return: List of vector IDs
        """
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
                # Generate valid UUID
                point_id = str(uuid.uuid4())
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
                logger.info(f"Stored batch of {len(points)} vectors successfully")
            except Exception as e:
                logger.error(f"Error storing vectors: {str(e)}")
                raise
        
        return vector_ids

    def search_similar(self, query_vector: List[float], paper_filter: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Qdrant with optional paper filtering.
        :param query_vector: Vector embedding of the query
        :param paper_filter: Optional list of paper filenames to filter results
        :param limit: Number of results to return
        :return: List of dictionaries with text, metadata, and score
        """
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": query_vector,
            "limit": limit
        }

        if paper_filter:
            search_params["query_filter"] = {
                "should": [
                    {"key": "file_name", "match": {"value": paper_name}}
                    for paper_name in paper_filter
                ]
            }

        results = self.client.search(**search_params)
        
        return [
            {
                "text": hit.payload["text"],
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                "score": hit.score
            }
            for hit in results
        ]
