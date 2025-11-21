"""
Main RAG pipeline orchestrating PDF processing, embedding generation, and vector storage.
Enhanced with context awareness, query classification, and hallucination prevention.
"""
from typing import List, Dict, Tuple, Optional
import os
import logging
import time
from src.services.pdf_processor import PDFProcessor
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore
from src.models.api_models import QueryResponse, Citation
from src.services.mongodb_service import MongoDBService
from src.services.query_classifier import QueryClassifier, QueryType
from src.services.section_matcher import SectionMatcher
from src.services.context_score_tracker import ContextScoreTracker
from src.services.sequential_summarizer import SequentialSummarizer
from src.services.llm_query_classifier import LLMQueryClassifier, QueryScope


# Configure logging
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        """Initialize all required services."""
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.mongodb = MongoDBService()
        # Original services
        self.query_classifier = QueryClassifier()
        self.section_matcher = SectionMatcher()
        self.context_tracker = ContextScoreTracker()
        self.sequential_summarizer = SequentialSummarizer()
        # LLM-based query classifier for accurate scope detection
        self.llm_classifier = LLMQueryClassifier()
        logger.info("✅ RAG Pipeline initialized with LLM Query Classifier")
    
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
        limit: int = 10
    ) -> QueryResponse:
        """
        Process query with full context awareness and hallucination prevention.
        Handles section-specific queries, global queries, and out-of-context requests.
        """
        start_time = time.time()
        logger.info(f"🧠 Query received: '{query_text}' | filter={paper_filter}")

        # ========== STEP 1: Use LLM to Classify Query Scope (Global vs Local) ==========
        llm_classification = self.llm_classifier.classify(query_text)
        query_scope = llm_classification["scope"]
        is_global = llm_classification["is_global"]
        global_operation = llm_classification.get("operation")
        
        logger.info(f"🤖 LLM Classification: SCOPE={query_scope}, OPERATION={global_operation}")
        logger.info(f"📊 Reasoning: {llm_classification.get('reason', 'N/A')}")

        # ========== STEP 1B: Handle Out-of-Context Queries ==========
        if query_scope == QueryScope.OUT_OF_CONTEXT:
            logger.info(f"💬 Out-of-context query detected")
            answer_response = await self.embedding_service.handle_out_of_context_query(
                query_text,
                "greeting"
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            return QueryResponse(
                answer=answer_response["answer"],
                citations=[],
                sources_used=[],
                confidence=1.0,
                context_score=1.0,
                context_level="high",
                query_type="out_of_context",
                is_out_of_context=True,
                retrieval_count=0,
                response_time_ms=response_time
            )

        # ========== STEP 2: Retrieve Context Based on Scope ==========
        if is_global:
            # GLOBAL SCOPE: Get chunks from all papers
            logger.info(f"🌍 GLOBAL QUERY: Operation={global_operation}")
            logger.info("📚 Retrieving chunks from ALL papers for context...")
            
            query_vector = self.embedding_service.get_embedding(query_text)
            results = self.vector_store.search_similar(
                query_vector=query_vector,
                paper_filter=paper_filter,
                limit=min(limit * 2, 20)  # Get more chunks for global operations
            )
            
            detected_section = None  # No specific section for global queries
            
        else:
            # LOCAL SCOPE: Get specific sections using keyword matching
            logger.info(f"🎯 LOCAL QUERY: Finding relevant sections...")
            
            # Use keyword-based classification to detect section
            keyword_classification = self.query_classifier.classify(query_text)
            detected_section = keyword_classification.get("detected_section")
            
            if detected_section:
                logger.info(f"🔍 Detected section: {detected_section}")
                
                # Get paper list if not filtered
                if not paper_filter:
                    papers = await self.mongodb.get_papers()
                    paper_filter = [p.id for p in papers]
                
                # Retrieve chunks specifically from the detected section
                results = await self.section_matcher.retrieve_section(
                    query=query_text,
                    section_name=detected_section,
                    paper_filter=paper_filter,
                    limit=limit
                )
            else:
                # No specific section detected, do standard retrieval
                logger.info("📖 No specific section detected, using standard retrieval")
                query_vector = self.embedding_service.get_embedding(query_text)
                results = self.vector_store.search_similar(
                    query_vector=query_vector,
                    paper_filter=paper_filter,
                    limit=limit
                )

        retrieval_count = len(results)
        logger.info(f"✅ Retrieved {retrieval_count} candidate chunks")

        # ========== STEP 4: Calculate Context Score ==========
        retrieval_scores = self.context_tracker.extract_retrieval_scores(results)
        source_diversity = self.context_tracker.calculate_source_diversity(
            [r.get("metadata", {}).get("file_name", "unknown") for r in results]
        )
        
        context_score, confidence_level = self.context_tracker.calculate_context_score(
            retrieval_scores,
            query_coverage=min(1.0, len(retrieval_scores) / 5.0),
            source_diversity=source_diversity
        )
        
        logger.info(f"📊 Context Score: {context_score:.2f} ({confidence_level})")

        # ========== STEP 5: Handle Low Confidence ==========
        clarification_needed = False
        clarification_prompt = None
        warning_message = None

        if self.context_tracker.is_low_confidence(context_score):
            logger.warning(f"⚠️ Low confidence detected ({context_score:.2f})")
            
            # Check if clarification should be requested
            if self.context_tracker.should_ask_for_clarification(
                context_score,
                len(query_text),
                retrieval_count
            ):
                clarification_needed = True
                clarification_prompt = (
                    "I found limited information on this topic. "
                    "Could you provide more details about what you're looking for? "
                    "For example, which paper or which section?"
                )
            
            # Generate warning message
            warning_message = self.context_tracker.generate_low_confidence_warning(context_score)

        # If no results at all, return early
        if not results:
            logger.warning("⚠️ No results found in Qdrant for the query.")
            query_type_str = "global" if is_global else "local"
            return QueryResponse(
                answer=clarification_prompt or "I couldn't find relevant information in the papers. Could you rephrase your question?",
                citations=[],
                sources_used=[],
                confidence=0.0,
                context_score=0.0,
                context_level="very_low",
                query_type=query_type_str,
                is_out_of_context=False,
                clarification_needed=True,
                clarification_prompt=clarification_prompt,
                warning_message="No relevant information found in papers.",
                retrieval_count=0,
                response_time_ms=(time.time() - start_time) * 1000
            )

        # ========== STEP 6: Generate Answer with Hallucination Prevention ==========
        json_response = await self.embedding_service.generate_answer(query_text, results)
        logger.debug(f"🧾 Gemini response: {json_response}")

        # Check hallucination risk
        hallucination_risk, risk_level = self.context_tracker.calculate_hallucination_risk(
            context_score,
            retrieval_count,
            source_diversity
        )
        logger.info(f"🛡️ Hallucination Risk: {hallucination_risk:.2f} ({risk_level})")

        if hallucination_risk > 0.6:
            hallucination_warning = self.context_tracker.generate_hallucination_prevention_prompt(context_score)
            if hallucination_warning and not warning_message:
                warning_message = hallucination_warning

        # ========== STEP 7: Build Response ==========
        citations = [Citation(**c) for c in json_response.get("citations", [])]
        
        # Determine query type string for response
        query_type_str = "global" if is_global else "local"

        response = QueryResponse(
            answer=json_response.get("answer", ""),
            citations=citations,
            sources_used=json_response.get("sources_used", []),
            confidence=json_response.get("confidence", 0.0),
            # New fields
            context_score=context_score,
            context_level=confidence_level,
            query_type=query_type_str,
            detected_section=detected_section,
            is_out_of_context=False,
            clarification_needed=clarification_needed,
            clarification_prompt=clarification_prompt,
            warning_message=warning_message,
            retrieval_count=retrieval_count,
            response_time_ms=(time.time() - start_time) * 1000
        )

        # ========== STEP 8: Update Paper Stats ==========
        for paper_file in response.sources_used:
            try:
                await self.mongodb.update_paper_stats(
                    paper_id=paper_file,
                    query_data={
                        "citations": [c.dict() for c in citations if c.paper_title == paper_file],
                        "response_time": response.response_time_ms,
                        "success": True,
                        "query_text": query_text,
                        "context_score": context_score
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