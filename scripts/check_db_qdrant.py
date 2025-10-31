# """
# Check stored data in MongoDB and Qdrant.
# """
# import os
# from pymongo import MongoClient
# from qdrant_client import QdrantClient

# # ----------------------------
# # MongoDB Setup
# # ----------------------------
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# DB_NAME = os.getenv("MONGO_DB", "research_db")
# COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "papers")

# mongo_client = MongoClient(MONGO_URI)
# db = mongo_client[DB_NAME]
# collection = db[COLLECTION_NAME]

# print("=== MongoDB Data ===")
# print(f"Database: {DB_NAME}, Collection: {COLLECTION_NAME}")

# try:
#     documents = list(collection.find())
#     print(f"Total documents: {len(documents)}\n")
#     for doc in documents:
#         print(doc)
# except Exception as e:
#     print(f"Error fetching MongoDB data: {e}")

# # ----------------------------
# # Qdrant Setup
# # ----------------------------
# # ----------------------------
# # Qdrant Setup
# # ----------------------------
# import os
# from qdrant_client import QdrantClient
# import json

# QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
# QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
# QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "research_papers")

# qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# print("\n" + "="*80)
# print(f"{'QDRANT COLLECTION DATA':^80}")
# print("="*80)
# print(f"Collection Name: {QDRANT_COLLECTION}")
# print(f"Host: {QDRANT_HOST}:{QDRANT_PORT}")
# print("="*80 + "\n")

# try:
#     # Scroll retrieves points in batches; here we limit to first 20
#     points, _ = qdrant_client.scroll(collection_name=QDRANT_COLLECTION, limit=20)
#     print(f"📊 Total points fetched: {len(points)}\n")
    
#     for idx, point in enumerate(points, 1):
#         vector_len = len(point.vector) if point.vector is not None else 0
        
#         print(f"\n{'─'*80}")
#         print(f"🔹 POINT #{idx}")
#         print(f"{'─'*80}")
        
#         # ID
#         print(f"\n📌 ID: {point.id}")
        
#         # Vector info
#         print(f"📐 Vector Length: {vector_len}")
        
#         # Payload
#         print(f"\n📦 PAYLOAD:")
#         if point.payload:
#             # File information
#             print(f"\n  📄 File Information:")
#             print(f"     • File Name: {point.payload.get('file_name', 'N/A')}")
#             print(f"     • Source: {point.payload.get('source', 'N/A')}")
#             print(f"     • Section: {point.payload.get('section', 'N/A')}")
#             print(f"     • Chunk Index: {point.payload.get('chunk_index', 'N/A')}")
#             print(f"     • Page Count: {point.payload.get('page_count', 'N/A')}")
            
#             # Paper metadata
#             print(f"\n  📚 Paper Metadata:")
#             print(f"     • Title: {point.payload.get('title', 'N/A')}")
#             print(f"     • Author(s): {point.payload.get('author', 'N/A')}")
#             print(f"     • Keywords: {point.payload.get('keywords', 'N/A')}")
            
#             # Text content (truncated for readability)
#             text = point.payload.get('text', '')
#             if text:
#                 print(f"\n  📝 Text Content:")
#                 # Show first 300 characters with proper wrapping
#                 display_text = text[:300] + "..." if len(text) > 300 else text
#                 # Wrap text to 70 characters per line
#                 wrapped_lines = [display_text[i:i+70] for i in range(0, len(display_text), 70)]
#                 for line in wrapped_lines:
#                     print(f"     {line}")
#         else:
#             print("     (No payload data)")
        
#         print(f"\n{'─'*80}")
    
#     print(f"\n{'='*80}")
#     print(f"{'END OF DATA':^80}")
#     print(f"{'='*80}\n")

# except Exception as e:
#     print(f"❌ Error fetching Qdrant data: {e}")


from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")  # adjust host if needed
collection_name = "research_papers"

# Scroll through points
points, next_page = client.scroll(collection_name=collection_name, limit=10)

scroll_result, _ = client.scroll(collection_name="research_papers", limit=5)
for p in scroll_result:
    print(f"ID: {p.id}")
    print(f"source: {p.payload.get('source')}")
    print(f"file_name: {p.payload.get('file_name')}")
    print("----")

# from qdrant_client import QdrantClient

# client = QdrantClient("localhost", port=6333)
# client.delete_collection(collection_name="research_papers")