"""
Service for generating embeddings and answers using sentence-transformers and Gemini.
Includes hallucination prevention and out-of-context query handling.
"""
import os
from typing import List, Union, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from src.models.paper import Chunk
import json
import re
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model and Gemini."""
        # Initialize embedding model
        self.model = SentenceTransformer(model_name)
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.gemini = genai.GenerativeModel('gemini-2.5-flash')

    def get_embeddings(self, texts: Union[str, List[str], List[Chunk]]) -> List[List[float]]:
        """Generate embeddings for the given texts."""
        if isinstance(texts, str):
            texts = [texts]
        elif isinstance(texts[0], Chunk):
            texts = [chunk.text for chunk in texts]
            
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.get_embeddings([text])[0]

    async def generate_answer(self, query: str, relevant_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate answer using Gemini and return structured JSON including only used chunks as citations.
        Includes hallucination prevention with strict context requirements.
        """
        # Prepare context string
        context = "\n\n".join([
            f"[From {chunk.get('metadata', {}).get('source', 'unknown')}, "
            f"Section: {chunk.get('metadata', {}).get('section', 'unknown')}, "
            f"Page: {chunk.get('metadata', {}).get('page', 1)}]\n"
            f"{chunk.get('text', '')}"
            for chunk in relevant_chunks
        ])

        # Construct enhanced prompt with hallucination prevention
        prompt = f"""
You are a research assistant powered by Retrieval Augmented Generation (RAG).

**CRITICAL INSTRUCTIONS - Must Follow Strictly:**
1. Answer ONLY using information from the provided context.
2. DO NOT add any information not explicitly stated in the context.
3. DO NOT speculate, assume, or infer beyond what is provided.
4. If the answer cannot be found in the context, say "I couldn't find this information in the provided papers."
5. Always cite the source paper, section, and page number for every claim.

Return your output strictly as a JSON object with this exact format:

{{
    "answer": "Your answer here",                 
    "citations": [
        {{
            "paper_title": "Paper Title (not filename)",
            "section": "Section Name",
            "page": 1,
            "relevance_score": 0.95
        }}
    ],
    "sources_used": ["paper1.pdf", "paper2.pdf"],          
    "confidence": 0.9,
    "found_relevant_info": true
}}

Context chunks from papers:
{context}

User Question: {query}

Guidelines:
- Set found_relevant_info to false if the context doesn't adequately address the query
- Confidence score should reflect how well the context answers the question (0-1)
- Include a citation only for chunks you actually used in the answer
- If multiple sources address the question, cite all of them
- Be honest about limitations in the provided context
"""

        # Call Gemini
        response = self.gemini.generate_content(prompt)

        # Strip Markdown code block if present
        text = response.text
        text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

        # Parse JSON safely
        try:
            json_output = json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            json_output = {
                "answer": text,
                "citations": [],
                "sources_used": list({chunk.get("metadata", {}).get("file_name", "unknown") 
                                    for chunk in relevant_chunks}),
                "confidence": 0.5,
                "found_relevant_info": False
            }

        # Ensure sources_used is always set
        if "sources_used" not in json_output or not json_output["sources_used"]:
            json_output["sources_used"] = list({chunk.get("metadata", {}).get("file_name", "unknown") 
                                            for chunk in relevant_chunks})

        # Add flag for hallucination detection
        if "found_relevant_info" not in json_output:
            json_output["found_relevant_info"] = json_output.get("confidence", 0.5) > 0.4

        return json_output

    async def handle_out_of_context_query(self, query: str, category: str) -> Dict[str, Any]:
        """
        Handle queries that are out of research context (greetings, meta questions).
        
        Args:
            query: User query
            category: Category of out-of-context query (greeting, casual, meta)
        
        Returns:
            Appropriate response based on category
        """
        responses = {
            "greeting": (
                "Hello! I'm your Research Paper Assistant. I'm here to help you explore and understand "
                "the research papers you've uploaded. You can ask me about specific sections, request summaries, "
                "or get explanations about concepts. What would you like to know?"
            ),
            "casual": (
                "I appreciate that! I'm here and ready to help you with your research papers. "
                "What aspect of the papers would you like to discuss?"
            ),
            "meta": (
                "I'm a Research Paper RAG Assistant. Here's what I can do:\n"
                "• Find information in specific sections (abstract, methodology, results, conclusion, etc.)\n"
                "• Summarize papers or specific sections\n"
                "• Compare content across multiple papers\n"
                "• Explain complex concepts from the papers\n"
                "• Translate or simplify technical content\n"
                "• Extract key findings and citations\n\n"
                "Just ask me anything about your uploaded research papers!"
            ),
        }

        answer = responses.get(category, responses["greeting"])

        return {
            "answer": answer,
            "citations": [],
            "sources_used": [],
            "confidence": 1.0,
            "found_relevant_info": True,
            "is_out_of_context": True
        }
    
