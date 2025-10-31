"""
Main RAG pipeline orchestrating PDF processing, embedding generation, and vector storage.
"""
from typing import List, Dict, Tuple, Optional
import os
import logging
from src.services.pdf_processor import PDFProcessor
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore
from src.models.api_models import QueryResponse, Citation
from src.services.mongodb_service import MongoDBService


# Configure logging
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        """Initialize all required services."""
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.mongodb = MongoDBService()
    
    def process_directory(self, directory_path: str):
        """Process all PDFs in a directory and store their vectors."""
        print("Processing PDFs and creating chunks...")
        pdf_files = [
            f for f in os.listdir(directory_path)
            if f.lower().endswith(".pdf")
        ]

        for pdf_file in pdf_files:
            file_path = os.path.join(directory_path, pdf_file)

            # ✅ Step 1: Check if PDF already exists in MongoDB
            if self.mongodb.paper_exists(pdf_file):
                print(f"✅ Skipping '{pdf_file}' — already stored in MongoDB.")
                continue

            print(f"📄 Processing '{pdf_file}'...")

            # ✅ Step 2: Extract text chunks from PDF
            chunks = self.pdf_processor.process_pdf(file_path)
            if not chunks:
                print(f"⚠️ No text extracted from {pdf_file}")
                continue

            # ✅ Step 3: Generate embeddings
            print(f"🔹 Generating embeddings for '{pdf_file}'...")
            vectors = self.embedding_service.get_embeddings(chunks)

            # ✅ Step 4: Store embeddings in vector database
            print(f"💾 Storing vectors in vector store...")
            self.vector_store.store_vectors(chunks, vectors)

            # ✅ Step 5: Store metadata & chunks in MongoDB
            print(f"📚 Saving '{pdf_file}' record in MongoDB...")
            self.mongodb.save_pdf_record(pdf_file, chunks)

            print(f"✅ Completed processing '{pdf_file}'.\n")

        print("📚 All PDFs processed successfully.")
    
    async def query(
        self,
        query_text: str,
        paper_filter: Optional[List[str]] = None,
        limit: int = 20
    ) -> QueryResponse:
        logger.info(f"🧠 Query received: '{query_text}' | filter={paper_filter}")

        # 1. Generate embedding
        query_vector = self.embedding_service.get_embedding(query_text)
        logger.debug(f"Generated query vector of length {len(query_vector)}")

        # 2. Retrieve top-k chunks
        results = self.vector_store.search_similar(
            query_vector=query_vector,
            paper_filter=paper_filter,
            limit=limit
        )

        if not results:
            logger.warning("⚠️ No results found in Qdrant for the query.")
            return QueryResponse(
                answer="No relevant information found.",
                citations=[],
                sources_used=[],
                confidence=0.0
            )

        logger.info(f"✅ Retrieved {len(results)} candidate chunks")

        # 3. Generate answer with structured JSON
        json_response = await self.embedding_service.generate_answer(query_text, results)
        logger.debug(f"🧾 Gemini response: {json_response}")

        # 4. Convert JSON into QueryResponse Pydantic model
        citations = [Citation(**c) for c in json_response.get("citations", [])]

        response = QueryResponse(
            answer=json_response.get("answer", ""),
            citations=citations,
            sources_used=json_response.get("sources_used", []),
            confidence=json_response.get("confidence", 0.0)
        )

        # 5. ✅ Update paper stats for each paper referenced
        for paper_file in response.sources_used:
            try:
                await self.mongodb.update_paper_stats(
                    paper_id=paper_file,
                    query_data={
                        "citations": [c.dict() for c in citations if c.paper_title == paper_file],
                        "response_time": 0.0,  # optionally measure
                        "success": True,
                        "query_text": query_text
                    }
                )
            except Exception as e:
                logger.error(f"Failed to update stats for {paper_file}: {e}")

        return response
# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Initialize pipeline
        pipeline = RAGPipeline()
        
        # Process PDFs from sample_papers directory
        sample_papers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_papers")
        pipeline.process_directory(sample_papers_dir)
        
        # Example queries
        example_queries = [
            "What are the title of the papers? ",
            "what are the conclusions of the papers? provide for all the papers",
        ]
        
        print("\nExample Queries:")
        for query in example_queries:
            print(f"\nQuery: {query}")
            print("\nGenerating answer...")
            
            answer, chunks = await pipeline.query(query)
            
            print("\nRelevant Chunks Used:")
            for i, chunk in enumerate(chunks, 1):
                # Safely get source
                source = chunk.get('metadata', {}).get('source', 'unknown')
                section = chunk.get('metadata', {}).get('section', 'unknown')
                text_preview = chunk.get('text', '')[:150]

                print(f"\nChunk {i} (Score: {chunk.get('score', 0.0):.3f}):")
                print(f"Source: {source}")
                print(f"Section: {section}")
                print(f"Text: {text_preview}...")

            print("\nGenerated Answer:")
            print(answer)
            print("\n" + "="*80)
    
    # Run the async main function
    asyncio.run(main())