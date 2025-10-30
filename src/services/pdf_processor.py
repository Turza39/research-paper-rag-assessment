"""
Service for processing PDF files with intelligent chunking and metadata extraction.
"""
import os
import re
import logging
from typing import Dict, List, Tuple
from datetime import datetime
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.models.paper import Paper, Section, Chunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self):
        """Initialize with intelligent chunking strategy."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=[
                "\n## ",
                "\n\n",
                ".\n",
                ". ",
                "?\n",
                "? ",
                "\n",
                " ",
                ""
            ]
        )

    # -----------------------------------------------------------
    # 🧩 NEWLY RESTORED METHOD
    # -----------------------------------------------------------
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, Dict[str, any]]:
        """Extract raw text and metadata from a PDF file."""
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            text = ""
            metadata = {
                'page_count': len(pdf.pages),
                'file_name': os.path.basename(file_path),
                'file_path': file_path,
                'title': '',
                'author': '',
                'keywords': ''
            }

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n## Page {i+1}\n\n{page_text}\n\n"

            # Extract PDF metadata
            if pdf.metadata:
                metadata.update({
                    'title': pdf.metadata.get('/Title', '').strip(),
                    'author': pdf.metadata.get('/Author', '').strip(),
                    'keywords': pdf.metadata.get('/Keywords', '').strip()
                })

            # Fallback to first page if metadata missing
            if not metadata['title'] or not metadata['author']:
                first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if not metadata['title'] and lines:
                    metadata['title'] = lines[0]
                if not metadata['author'] and len(lines) > 1:
                    metadata['author'] = lines[1]

        return text, metadata

    # -----------------------------------------------------------
    def create_chunks(self, text: str, file_metadata: Dict[str, any], max_chunk_size: int = 1000) -> List[Chunk]:
        """Create text chunks preserving section-level context."""
        text_chunks = []
        file_metadata = {**file_metadata, 'source': file_metadata.get('file_name', 'unknown')}

        # 1. Handle special sections
        special_sections = {}
        if file_metadata.get('title'):
            special_sections['Title'] = file_metadata['title']
        if file_metadata.get('author'):
            special_sections['Authors'] = file_metadata['author']
        if file_metadata.get('keywords'):
            special_sections['Keywords'] = file_metadata['keywords']

        for section_name, section_text in special_sections.items():
            if section_text.strip():
                text_chunks.append(Chunk(
                    text=section_text.strip(),
                    metadata={**file_metadata, 'section': section_name, 'chunk_index': len(text_chunks)}
                ))

        # 2. Abstract detection
        abstract_match = re.search(r'Abstract[:\s]*(.+?)(?=\n##|\Z)', text, re.IGNORECASE | re.DOTALL)
        if abstract_match:
            abstract_text = abstract_match.group(1).strip()
            text_chunks.append(Chunk(
                text=abstract_text,
                metadata={**file_metadata, 'section': 'Abstract', 'chunk_index': len(text_chunks)}
            ))

        # 3. Paragraph-based chunking
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for para in paragraphs:
            if len(para) <= max_chunk_size:
                text_chunks.append(Chunk(
                    text=para,
                    metadata={**file_metadata, 'section': 'Paragraph', 'chunk_index': len(text_chunks)}
                ))
            else:
                start = 0
                while start < len(para):
                    end = min(start + max_chunk_size, len(para))
                    chunk_text = para[start:end].strip()
                    text_chunks.append(Chunk(
                        text=chunk_text,
                        metadata={**file_metadata, 'section': 'Paragraph', 'chunk_index': len(text_chunks)}
                    ))
                    start += max_chunk_size

        return text_chunks

    # -----------------------------------------------------------
    def process_pdf(self, file_path: str) -> List[Chunk]:
        """Extract text and create chunks from a single PDF."""
        logger.info(f"Processing PDF: {os.path.basename(file_path)}")
        text, metadata = self.extract_text_from_pdf(file_path)
        return self.create_chunks(text, metadata)

    def process_directory(self, directory_path: str) -> List[Chunk]:
        """Process all PDFs in a directory."""
        all_chunks = []
        for filename in os.listdir(directory_path):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(directory_path, filename)
                try:
                    chunks = self.process_pdf(file_path)
                    all_chunks.extend(chunks)
                    logger.info(f"Processed {filename}: {len(chunks)} chunks created")
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
        return all_chunks
