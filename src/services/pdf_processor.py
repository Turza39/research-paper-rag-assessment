"""
Service for processing PDF files with intelligent chunking and metadata extraction.
"""
import os, uuid
from io import BytesIO
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
    # EXTRACT TEXT FROM PDF FILE
    # -----------------------------------------------------------
    def extract_text_from_pdf(self, file_path: str) -> tuple[str, dict]:
        """Extract text and metadata from PDF file."""
        try:
            pdf = PdfReader(file_path)
            text = ""
            metadata = {
                "page_count": len(pdf.pages),
                "title": "",
                "author": "",
                "keywords": "",
                "file_name": os.path.basename(file_path)
            }

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n## Page {i+1}\n\n{page_text}\n\n"

            # PDF metadata
            if pdf.metadata:
                metadata.update({
                    "title": pdf.metadata.get("/Title", "").strip(),
                    "author": pdf.metadata.get("/Author", "").strip(),
                    "keywords": pdf.metadata.get("/Keywords", "").strip(),
                })

            # fallback title from first page
            if not metadata["title"] and pdf.pages:
                first_page_text = pdf.pages[0].extract_text() or ""
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if lines:
                    metadata["title"] = lines[0]

            return text, metadata
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return "", {"file_name": os.path.basename(file_path)}

    # -----------------------------------------------------------
    # EXTRACT TEXT FROM PDF BYTES (For file uploads)
    # -----------------------------------------------------------
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> tuple[str, dict]:
        """Extract text and metadata from PDF bytes (for file uploads)."""
        try:
            pdf = PdfReader(BytesIO(pdf_bytes))
            text = ""
            metadata = {
                "page_count": len(pdf.pages),
                "title": "",
                "author": "",
                "keywords": "",
            }

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n## Page {i+1}\n\n{page_text}\n\n"

            # PDF metadata
            if pdf.metadata:
                metadata.update({
                    "title": pdf.metadata.get("/Title", "").strip(),
                    "author": pdf.metadata.get("/Author", "").strip(),
                    "keywords": pdf.metadata.get("/Keywords", "").strip(),
                })

            # fallback title from first page
            if not metadata["title"] and pdf.pages:
                first_page_text = pdf.pages[0].extract_text() or ""
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if lines:
                    metadata["title"] = lines[0]

            return text, metadata
        except Exception as e:
            logger.error(f"Error extracting text from PDF bytes: {e}")
            return "", {"title": "", "author": "", "keywords": "", "page_count": 0}

    # -----------------------------------------------------------
    # DETECT MAJOR SECTIONS IN TEXT
    # -----------------------------------------------------------
    def detect_sections(self, text: str) -> Dict[str, str]:
        """
        Detect major research paper sections using regex patterns.
        Returns dict mapping section names to their content.
        """
        sections = {}
        
        # Section patterns (case-insensitive, with boundary handling)
        section_patterns = {
            "Introduction": r"(?:^|\n)\s*(?:1\.|I\.?)\s*(?:INTRODUCTION|INTRO)[\s:\n]+(.*?)(?=\n\s*(?:2\.|II\.?|[A-Z][A-Z\s]+)|\Z)",
            "Related Work": r"(?:^|\n)\s*(?:\d+\.|[A-Z]+\.?)\s*(?:RELATED\s+WORK|LITERATURE\s+REVIEW)[\s:\n]+(.*?)(?=\n\s*(?:\d+\.|[A-Z][A-Z\s]+)|\Z)",
            "Methodology": r"(?:^|\n)\s*(?:\d+\.|[A-Z]+\.?)\s*(?:METHODOLOGY|METHOD|APPROACH|FRAMEWORK|SYSTEM|DESIGN)[\s:\n]+(.*?)(?=\n\s*(?:\d+\.|[A-Z][A-Z\s]+)|\Z)",
            "Results": r"(?:^|\n)\s*(?:\d+\.|[A-Z]+\.?)\s*(?:RESULTS|EXPERIMENTS|EXPERIMENTAL|FINDINGS|EVALUATION|PERFORMANCE)[\s:\n]+(.*?)(?=\n\s*(?:\d+\.|[A-Z][A-Z\s]+)|\Z)",
            "Discussion": r"(?:^|\n)\s*(?:\d+\.|[A-Z]+\.?)\s*(?:DISCUSSION|ANALYSIS|IMPLICATIONS)[\s:\n]+(.*?)(?=\n\s*(?:\d+\.|[A-Z][A-Z\s]+)|\Z)",
            "Conclusion": r"(?:^|\n)\s*(?:\d+\.|[A-Z]+\.?)\s*(?:CONCLUSION|CONCLUSIONS|SUMMARY|FINAL\s+REMARKS)[\s:\n]+(.*?)(?=\n\s*(?:REFERENCES|BIBLIOGRAPHY|\d+\.|[A-Z][A-Z\s]+)|\Z)",
            "References": r"(?:^|\n)\s*(?:REFERENCES|BIBLIOGRAPHY|WORKS\s+CITED)[\s:\n]+(.*?)(?=\Z)",
            "Abstract": r"(?:^|\n)\s*(?:ABSTRACT)[\s:\n]+(.*?)(?=\n\s*(?:1\.|INTRODUCTION|[A-Z][A-Z\s]{5,})|\Z)",
        }
        
        text_upper = text.upper()
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text_upper, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if match:
                section_text = text[match.start(1):match.end(1)].strip()
                if len(section_text) > 50:  # Only keep substantial sections
                    sections[section_name] = section_text
                    logger.info(f"✅ Detected {section_name}: {len(section_text)} chars")
                else:
                    logger.debug(f"⏭️ Skipped {section_name}: Too short ({len(section_text)} chars)")
            else:
                logger.debug(f"❌ Could not detect {section_name}")
        
        return sections

    # -----------------------------------------------------------
    def create_chunks(self, text: str, file_metadata: Dict[str, any], max_chunk_size: int = 1000) -> List[Chunk]:
        """
        Create text chunks with proper section detection.
        
        Strategy:
        1. Detect major sections (Introduction, Methodology, Results, etc.)
        2. Create chunks from each section with proper labels
        3. For undetected text, use paragraph-based chunking
        """
        import uuid
        text_chunks = []

        # Ensure both 'source' and 'file_name' exist
        file_name = file_metadata.get("file_name", "unknown")
        file_metadata = {**file_metadata, 'source': file_name, 'file_name': file_name}

        # 1. Create metadata chunks (title, author, keywords)
        if file_metadata.get('title'):
            unique_id = str(uuid.uuid4())
            text_chunks.append(Chunk(
                text=file_metadata['title'].strip(),
                metadata={
                    **file_metadata,
                    'section': 'Title',
                    'chunk_index': len(text_chunks),
                    'vector_id': unique_id
                }
            ))

        if file_metadata.get('author'):
            unique_id = str(uuid.uuid4())
            text_chunks.append(Chunk(
                text=file_metadata['author'].strip(),
                metadata={
                    **file_metadata,
                    'section': 'Authors',
                    'chunk_index': len(text_chunks),
                    'vector_id': unique_id
                }
            ))

        # 2. Detect and chunk major sections
        detected_sections = self.detect_sections(text)
        processed_text = ""

        for section_name, section_text in detected_sections.items():
            # Create chunks from section text
            if len(section_text) <= max_chunk_size:
                unique_id = str(uuid.uuid4())
                text_chunks.append(Chunk(
                    text=section_text,
                    metadata={
                        **file_metadata,
                        'section': section_name,
                        'chunk_index': len(text_chunks),
                        'vector_id': unique_id
                    }
                ))
            else:
                # Split large sections into multiple chunks
                start = 0
                chunk_num = 0
                while start < len(section_text):
                    end = min(start + max_chunk_size, len(section_text))
                    chunk_text = section_text[start:end].strip()
                    if chunk_text:
                        unique_id = str(uuid.uuid4())
                        text_chunks.append(Chunk(
                            text=chunk_text,
                            metadata={
                                **file_metadata,
                                'section': section_name,
                                'chunk_index': len(text_chunks),
                                'vector_id': unique_id
                            }
                        ))
                        chunk_num += 1
                    start = end

            processed_text += section_text + "\n\n"

        # 3. Handle remaining text (not matched to major sections)
        # Split into paragraphs and create chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and p not in processed_text]
        for para in paragraphs:
            if len(para) <= max_chunk_size:
                unique_id = str(uuid.uuid4())
                text_chunks.append(Chunk(
                    text=para,
                    metadata={
                        **file_metadata,
                        'section': 'Content',  # Generic section for unmatched paragraphs
                        'chunk_index': len(text_chunks),
                        'vector_id': unique_id
                    }
                ))
            else:
                # Split large paragraphs
                start = 0
                while start < len(para):
                    end = min(start + max_chunk_size, len(para))
                    chunk_text = para[start:end].strip()
                    if chunk_text:
                        unique_id = str(uuid.uuid4())
                        text_chunks.append(Chunk(
                            text=chunk_text,
                            metadata={
                                **file_metadata,
                                'section': 'Content',
                                'chunk_index': len(text_chunks),
                                'vector_id': unique_id
                            }
                        ))
                    start += max_chunk_size

        logger.info(f"Created {len(text_chunks)} chunks with {len(detected_sections)} detected sections")
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


