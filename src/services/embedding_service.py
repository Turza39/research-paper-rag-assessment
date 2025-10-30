"""
Service for generating embeddings and answers using sentence-transformers and Gemini.
"""
import os
from typing import List, Union, Dict
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from src.models.paper import Chunk
import json
from typing import List, Dict, Any
from src.models.paper import Chunk
import google.generativeai as genai
import os
import re


# Load environment variables
load_dotenv()

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
        """
        # Prepare context string
        context = "\n\n".join([
            f"[From {chunk.get('metadata', {}).get('source', 'unknown')}, "
            f"Section: {chunk.get('metadata', {}).get('section', 'unknown')}, "
            f"Page: {chunk.get('metadata', {}).get('page', 1)}]\n"
            f"{chunk.get('text', '')}"
            for chunk in relevant_chunks
        ])

        # Construct prompt for JSON
        prompt = f"""
    You are a research assistant. Answer the question using ONLY the provided context. 
    Return your output strictly as a JSON object in the following format:

    {{
        "answer": "...",                 
        "citations": [
            {{
                "paper_title": "...", ** give paper title, not file name
                "section": "...",
                "page": 1,
                "relevance_score": 0.0
            }}
        ],
        "sources_used": ["..."],          
        "confidence": 0.0
    }}

    Context chunks:
    {context}

    Question: {query}

    Instructions:
    1. Only use information from the context.
    2. Include a citation only if you used that chunk to generate your answer.
    3. Provide relevance_score for each citation (0-1).
    4. List sources_used as the unique filenames you referenced.
    5. Provide an overall confidence score (0-1).
    6. No need to be too much strict about the relavancy. 
    """

        # Call Gemini
        response = self.gemini.generate_content(prompt)

        # Strip Markdown code block if present
        text = response.text
        text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

        # Parse JSON safely
        try:
            json_output = json.loads(text)
        except Exception:
            json_output = {
                "answer": text,
                "citations": [],
                "sources_used": list({chunk.get("metadata", {}).get("file_name", "unknown") 
                                    for chunk in relevant_chunks}),
                "confidence": 0.0
            }

        # Ensure sources_used is always set
        if "sources_used" not in json_output or not json_output["sources_used"]:
            json_output["sources_used"] = list({chunk.get("metadata", {}).get("file_name", "unknown") 
                                            for chunk in relevant_chunks})

        return json_output
    
