import os
import PyPDF2
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
import google.generativeai as genai

# CONFIG
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "pdf_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200  # characters
TOP_K = 5

GEMINI_API_KEY = "AIzaSyBr9OVOkbBkbpjQaHWekvRjqk_pXqJRN9s"
GEMINI_MODEL = "gemini-2.5-pro"

def clean_text(text: str) -> str:
    """Clean extracted text"""
    text = text.replace('\x00', '')  # Remove null bytes
    text = ' '.join(text.split())  # Normalize whitespace
    return text.strip()

def chunk_text(text: str, page_num: int, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping character-based chunks"""
    text = clean_text(text)
    chunks = []
    start = 0
    chunk_idx = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        # Try to break at sentence/word boundary
        if end < len(text):
            # Look for last period, question mark, or exclamation
            last_break = max(
                chunk_text.rfind('. '),
                chunk_text.rfind('? '),
                chunk_text.rfind('! '),
                chunk_text.rfind('\n')
            )
            if last_break > chunk_size * 0.5:  # Only if break is in latter half
                end = start + last_break + 1
                chunk_text = text[start:end]
        
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text.strip(),
                "page": page_num,
                "chunk_index": chunk_idx,
                "char_start": start,
                "char_end": end,
                "char_count": len(chunk_text)
            })
            chunk_idx += 1
        
        # Move forward with overlap
        start = end - overlap if end < len(text) else len(text)
        
        # Safety: ensure forward progress
        if start <= chunks[-1]['char_start'] if chunks else 0:
            start = end
    
    return chunks

def index_pdf(pdf_path: str):
    """Index PDF with character-based chunking"""
    print(f"📄 Indexing: {pdf_path}")
    
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Recreate collection
    try:
        client.delete_collection(QDRANT_COLLECTION)
        print("🗑️ Deleted existing collection")
    except:
        pass
    
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=qmodels.VectorParams(size=EMBEDDING_DIM, distance=qmodels.Distance.COSINE)
    )
    print(f"✅ Created collection: {QDRANT_COLLECTION}")
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    point_id = 1
    batch = []
    pdf_name = os.path.basename(pdf_path)
    total_chars = 0
    
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        total_pages = len(reader.pages)
        
        print(f"\n📖 Processing {total_pages} pages...\n")
        
        for page_num, page in enumerate(reader.pages, 1):
            raw_text = page.extract_text() or ""
            
            if not raw_text.strip():
                print(f"  ⚠️  Page {page_num}: Empty")
                continue
            
            page_chars = len(raw_text)
            total_chars += page_chars
            
            chunks = chunk_text(raw_text, page_num)
            
            for chunk in chunks:
                vector = model.encode([chunk['text']])[0].tolist()
                batch.append(qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        **chunk,
                        "pdf_name": pdf_name
                    }
                ))
                point_id += 1
                
                if len(batch) >= 50:
                    client.upsert(collection_name=QDRANT_COLLECTION, points=batch)
                    batch = []
            
            print(f"  ✓ Page {page_num:3d}/{total_pages} | {page_chars:6d} chars → {len(chunks):3d} chunks")
    
    if batch:
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch)
    
    print(f"\n✅ Indexed {point_id - 1} chunks from {total_pages} pages ({total_chars:,} characters)")
    print(f"   Collection: {QDRANT_COLLECTION}")

def generate_answer(query: str, context: str) -> str:
    """Generate answer using Gemini"""
    if not GEMINI_API_KEY:
        raise ValueError("❌ GEMINI_API_KEY not set")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    prompt = f"""You are a helpful research assistant. Answer the question based on the provided context from a research paper.
Be concise, accurate, and cite page numbers when relevant. If the context doesn't contain the answer, say so clearly.

Context from research paper:
{context}

Question: {query}

Answer:"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Error generating answer: {e}"

def query_pdf(query: str, top_k: int = TOP_K, return_raw: bool = False):
    """Query indexed PDF"""
    print(f"\n🔍 Query: {query}")
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vec = model.encode([query])[0].tolist()
    
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    try:
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vec,
            limit=top_k
        )
    except Exception as e:
        return f"❌ Search error: {e}"
    
    if not results:
        return "❌ No results found. Index the PDF first."
    
    context_parts = []
    
    # --- Start of new display logic for context chunks ---
    print("\n📚 Top Retrieved Context Chunks (Top-K):")
    for idx, r in enumerate(results, 1):
        p = r.payload
        text = p['text']
        preview = text[:200] + "..." if len(text) > 200 else text
        print(f"\n--- Chunk {idx} (Score: {r.score:.4f} | Page {p['page']}, Index {p['chunk_index']}) ---")
        print(preview)
        
        # Also build the context string for the RAG prompt
        context_parts.append(
            f"[Page {p['page']}, Chunk {p['chunk_index']}]\n{p['text']}"
        )
    # --- End of new display logic ---
    
    context = "\n\n---\n\n".join(context_parts)
    
    if return_raw:
        return context
    
    print("\n🤖 Generating answer with Gemini...")
    answer = generate_answer(query, context)
    
    return answer, context # Keep returning context for the raw option and the original RAG logic

def show_chunks(num_chunks: int):
    """Show first N chunks from collection"""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    try:
        results, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=num_chunks
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Make sure you've indexed a PDF first with --index")
        return
    
    if not results:
        print("❌ No chunks found. Index a PDF first.")
        return
    
    print(f"\n📚 First {len(results)} chunks from collection:\n")
    
    for idx, point in enumerate(results, 1):
        p = point.payload
        print("=" * 80)
        print(f"Chunk {idx} | Page {p.get('page')} | Chunk Index: {p.get('chunk_index')} | Chars: {p.get('char_count')}")
        print("=" * 80)
        text = p.get('text', '')
        preview = text[:400] + "..." if len(text) > 400 else text
        print(preview)
        print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PDF RAG System with Qdrant and Gemini"
    )
    
    parser.add_argument("--pdf", help="PDF file to index")
    parser.add_argument("--index", action="store_true", help="Index the PDF")
    parser.add_argument("--query", help="Query the PDF")
    parser.add_argument("--raw", action="store_true", help="Show raw context only")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Number of chunks to retrieve")
    parser.add_argument("--show-chunks", type=int, metavar="N", help="Show first N chunks from collection")
    
    args = parser.parse_args()
    
    # Handle index
    if args.index:
        if not args.pdf:
            print("❌ Provide --pdf to index")
        else:
            index_pdf(args.pdf)
    
    # Handle show chunks
    elif args.show_chunks:
        show_chunks(args.show_chunks)
    
    # Handle query
    elif args.query:
        if args.raw:
            print("\n📄 Raw Context:\n")
            # When --raw is used, it still shows the top 5 chunks (new feature) but the final output is just the raw context
            print(query_pdf(args.query, top_k=args.top_k, return_raw=True))
        else:
            # query_pdf now prints the top-k chunks inside the function
            result = query_pdf(args.query, top_k=args.top_k)
            if isinstance(result, tuple):
                answer, context = result
                print("\n" + "=" * 80)
                print("✅ ANSWER:")
                print("=" * 80)
                print(answer)
                
                # REMOVED: The section that printed the full context chunks again
                # This achieves "no need to show context chunks in each query" for the final output
                # The top 5 chunks are now shown BEFORE the answer generation.
                
            else:
                print(result)
    
    else:
        parser.print_help()