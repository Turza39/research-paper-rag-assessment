"""
Wrapper module to expose QdrantClient for local imports.
This allows other modules to safely do:
    from src.services.qdrant_client import QdrantClient
"""

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Expose the QdrantClient class directly
QdrantClient = _QdrantClient
