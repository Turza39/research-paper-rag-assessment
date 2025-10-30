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

# Configure logging
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        """Initialize all required services."""
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
    
    def process_directory(self, directory_path: str):
        """Process all PDFs in a directory and store their vectors."""
        # Step 1: Process PDFs into chunks with rich metadata
        print("Processing PDFs and creating chunks...")
        chunks = self.pdf_processor.process_directory(directory_path)
        if not chunks:
            print(f"No PDF files found in {directory_path}")
            return
            
        # Step 2: Generate embeddings
        print("Generating embeddings...")
        vectors = self.embedding_service.get_embeddings(chunks)
        
        # Step 3: Store in vector store with metadata
        print("Storing vectors and metadata...")
        self.vector_store.store_vectors(chunks, vectors)
        
        print(f"Successfully processed {len(chunks)} chunks from directory: {directory_path}")
    
    async def query(self, query_text: str, paper_filter: Optional[List[str]] = None, limit: int = 10) -> QueryResponse:
        """
        Query the RAG system and generate an answer.
        Args:
            query_text: The question to answer
            paper_filter: Optional list of paper filenames to restrict search to
            limit: Maximum number of chunks to retrieve
        Returns:
            QueryResponse with answer, citations, and metadata
        """
        try:
            # Generate embedding for query
            query_vector = self.embedding_service.get_embedding(query_text)
            
            # Search for similar chunks with paper filtering
            results = self.vector_store.search_similar(
                query_vector=query_vector,
                paper_filter=paper_filter,
                limit=limit
            )
            
            if not results:
                return QueryResponse(
                    answer="No relevant information found in the specified papers.",
                    citations=[],
                    sources_used=[],
                    confidence=0.0
                )
            
            # Generate answer using Gemini
            answer = await self.embedding_service.generate_answer(query_text, results)
            
            # Create citations from results
            citations = []
            sources_used = set()
            
            for result in results:
                metadata = result["metadata"]
                paper_title = metadata.get("title", "Unknown")
                sources_used.add(metadata.get("file_name", ""))
                
                citations.append(Citation(
                    paper_title=paper_title,
                    section=metadata.get("section", "Unknown"),
                    page=metadata.get("page", 1),
                    relevance_score=float(result["score"])
                ))
            
            # Calculate overall confidence based on top citation scores
            confidence = max(min(sum(r["score"] for r in results[:3]) / 3, 1.0), 0.0) if results else 0.0
            
            return QueryResponse(
                answer=answer,
                citations=citations,
                sources_used=list(sources_used),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            raise

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