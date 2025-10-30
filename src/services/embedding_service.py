"""
Service for generating embeddings and answers using sentence-transformers and Gemini.
"""
import os
from typing import List, Union, Dict
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from src.models.paper import Chunk

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

    async def generate_answer(self, query: str, relevant_chunks: List[Dict[str, any]]) -> str:
        """
        Generate an answer using Gemini based on relevant chunks.

        Option 2: Safely handle missing 'source' key in chunk metadata.
        """
        # Prepare context from relevant chunks
        context = "\n\n".join([
            f"[From {chunk.get('metadata', {}).get('source', 'unknown')}, "
            f"Section: {chunk.get('metadata', {}).get('section', 'unknown')}]\n"
            f"{chunk.get('text', '')}"
            for chunk in relevant_chunks
        ])
        
        # Construct prompt
        prompt = f"""As a research assistant, please answer the following question based on the provided paper excerpts. 
Include only information that is directly supported by the given context.

Context from research papers:
{context}

Question: {query}

Please provide a clear, concise answer that:
1. Directly addresses the question
2. Uses information only from the provided context
3. Cites specific papers/sections when appropriate
4. Acknowledges if information is incomplete or unclear
"""

        # Generate response
        response = self.gemini.generate_content(prompt)
        return response.text
