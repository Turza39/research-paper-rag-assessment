"""
Main RAG pipeline orchestrating PDF processing, embedding generation, and vector storage.
"""
from typing import List, Dict, Tuple
import os
from src.services.pdf_processor import PDFProcessor
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore

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
    
    async def query(self, query_text: str, limit: int = 5) -> Tuple[str, List[Dict]]:
        """
        Query the RAG system and generate an answer.
        Returns both the generated answer and the relevant chunks used.
        """
        # Generate embedding for query
        query_vector = self.embedding_service.get_embedding(query_text)
        
        # Search for similar chunks
        results = self.vector_store.search_similar(query_vector, limit=limit)
        
        # Generate answer using Gemini
        answer = await self.embedding_service.generate_answer(query_text, results)
        
        return answer, results
        
        return results

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