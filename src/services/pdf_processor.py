"""
Service for processing PDF files with intelligent chunking and metadata extraction.
"""
import os, uuid
from io import BytesIO
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from PyPDF2 import PdfReader
from src.models.paper import Paper, Section, Chunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        """
        Initialize with intelligent section-based chunking strategy.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Flexible section keywords (case-insensitive matching)
        self.section_keywords = {
            "Abstract": ["abstract", "summary"],
            "Introduction": ["introduction", "intro", "background"],
            "Related Work": ["related work", "literature review", "previous work", "prior work"],
            "Methodology": ["methodology", "methods", "method", "approach", "proposed method", "materials and methods"],
            "System Design": ["system design", "system architecture", "architecture", "design", "implementation", "framework"],
            "Results": ["results", "experiments", "experimental results", "evaluation", "findings", "performance evaluation"],
            "Discussion": ["discussion", "analysis"],
            "Conclusion": ["conclusion", "conclusions", "concluding remarks", "summary and conclusion"],
            "References": ["references", "bibliography", "works cited"],
            "Acknowledgments": ["acknowledgment", "acknowledgments", "acknowledgement", "acknowledgements"],
            "Appendix": ["appendix", "appendices", "supplementary material"]
        }

    def extract_text_from_pdf(self, file_path: str) -> tuple[str, dict]:
        """Extract text and metadata from PDF file."""
        try:
            pdf = PdfReader(file_path)
            text = ""
            page_markers = []
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
                    page_markers.append(len(text))
                    text += page_text + "\n\n"

            # PDF metadata
            if pdf.metadata:
                metadata.update({
                    "title": pdf.metadata.get("/Title", "").strip(),
                    "author": pdf.metadata.get("/Author", "").strip(),
                    "keywords": pdf.metadata.get("/Keywords", "").strip(),
                })

            # Fallback title from first page
            if not metadata["title"] and pdf.pages:
                first_page_text = pdf.pages[0].extract_text() or ""
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if lines:
                    metadata["title"] = lines[0]

            metadata["page_markers"] = page_markers
            return text, metadata
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return "", {"file_name": os.path.basename(file_path), "page_markers": []}

    def extract_text_from_bytes(self, pdf_bytes: bytes, file_name: str = "uploaded.pdf") -> tuple[str, dict]:
        """Extract text and metadata from PDF bytes (for file uploads)."""
        try:
            pdf = PdfReader(BytesIO(pdf_bytes))
            text = ""
            page_markers = []
            metadata = {
                "page_count": len(pdf.pages),
                "title": "",
                "author": "",
                "keywords": "",
                "file_name": file_name
            }

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    page_markers.append(len(text))
                    text += page_text + "\n\n"

            # PDF metadata
            if pdf.metadata:
                metadata.update({
                    "title": pdf.metadata.get("/Title", "").strip(),
                    "author": pdf.metadata.get("/Author", "").strip(),
                    "keywords": pdf.metadata.get("/Keywords", "").strip(),
                })

            # Fallback title from first page
            if not metadata["title"] and pdf.pages:
                first_page_text = pdf.pages[0].extract_text() or ""
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if lines:
                    metadata["title"] = lines[0]

            metadata["page_markers"] = page_markers
            return text, metadata
        except Exception as e:
            logger.error(f"Error extracting text from PDF bytes: {e}")
            return "", {"title": "", "author": "", "keywords": "", "page_count": 0, "file_name": file_name, "page_markers": []}

    def is_section_header(self, text: str, start_pos: int, end_pos: int) -> Tuple[bool, Optional[str]]:
        """
        Check if text segment is a section header.
        
        Returns:
            (is_header, section_name)
        """
        segment = text[start_pos:end_pos].strip()
        
        # Must be reasonably short (not a paragraph)
        if len(segment) > 150 or len(segment) < 3:
            return False, None
        
        # Must not have too many lowercase words (headers are typically title case or uppercase)
        words = segment.split()
        if len(words) > 10:  # Headers are typically short
            return False, None
        
        # Check against known section keywords
        segment_lower = segment.lower()
        
        for section_name, keywords in self.section_keywords.items():
            for keyword in keywords:
                # Match with optional numbering prefix
                # Patterns: "Abstract:", "1. Introduction", "I. INTRODUCTION", "Introduction"
                patterns = [
                    f"^{re.escape(keyword)}\\s*:?\\s*$",  # "Abstract:" or "Abstract"
                    f"^\\d+\\.?\\s*{re.escape(keyword)}\\s*:?\\s*$",  # "1. Introduction"
                    f"^[IVX]+\\.?\\s*{re.escape(keyword)}\\s*:?\\s*$",  # "I. INTRODUCTION"
                    f"^[A-Z]\\.\\s*{re.escape(keyword)}",  # "A. Background"
                ]
                
                for pattern in patterns:
                    if re.match(pattern, segment_lower, re.IGNORECASE):
                        logger.debug(f"✅ Detected section: {section_name} | Text: '{segment[:50]}'")
                        return True, section_name
        
        return False, None

    def find_all_sections(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all section boundaries in the text using flexible pattern matching.
        
        Returns:
            List of tuples: (start_pos, end_pos, section_name)
        """
        sections = []
        lines = text.split('\n')
        current_pos = 0
        
        for line in lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            
            # Check if this line is a section header
            is_header, section_name = self.is_section_header(text, line_start, line_end)
            
            if is_header and section_name:
                sections.append((line_start, line_end, section_name))
            
            current_pos = line_end + 1  # +1 for newline character
        
        logger.info(f"🔍 Found {len(sections)} sections")
        for i, (start, end, name) in enumerate(sections):
            preview = text[start:end].strip()[:60]
            logger.info(f"  {i+1}. {name} at pos {start}: '{preview}'")
        
        return sections

    def get_page_number(self, char_position: int, page_markers: List[int]) -> int:
        """Calculate page number based on character position."""
        if not page_markers:
            return 1
            
        for i, marker in enumerate(page_markers):
            if char_position < marker:
                return max(1, i)
        return len(page_markers)

    def create_overlapping_chunks(
        self, 
        text: str, 
        section_name: str, 
        file_metadata: Dict, 
        start_char_pos: int
    ) -> List[Chunk]:
        """Split text into overlapping chunks while preserving context."""
        chunks = []
        text_length = len(text)
        page_markers = file_metadata.get("page_markers", [])
        
        if text_length <= self.chunk_size:
            unique_id = str(uuid.uuid4())
            page_num = self.get_page_number(start_char_pos, page_markers)
            
            chunks.append(Chunk(
                text=text.strip(),
                metadata={
                    "file_name": file_metadata.get("file_name", "unknown"),
                    "source": file_metadata.get("file_name", "unknown"),
                    "section": section_name,
                    "page": page_num,
                    "chunk_index": 0,
                    "vector_id": unique_id,
                    "title": file_metadata.get("title", ""),
                    "author": file_metadata.get("author", ""),
                    "keywords": file_metadata.get("keywords", ""),
                    "page_count": file_metadata.get("page_count", 0)
                },
                vector_id=unique_id
            ))
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            if end < text_length:
                search_start = max(end - 100, start)
                sentence_end = max(
                    text.rfind('. ', search_start, end),
                    text.rfind('.\n', search_start, end),
                    text.rfind('?\n', search_start, end),
                    text.rfind('!\n', search_start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                unique_id = str(uuid.uuid4())
                current_char_pos = start_char_pos + start
                page_num = self.get_page_number(current_char_pos, page_markers)
                
                chunks.append(Chunk(
                    text=chunk_text,
                    metadata={
                        "file_name": file_metadata.get("file_name", "unknown"),
                        "source": file_metadata.get("file_name", "unknown"),
                        "section": section_name,
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "vector_id": unique_id,
                        "title": file_metadata.get("title", ""),
                        "author": file_metadata.get("author", ""),
                        "keywords": file_metadata.get("keywords", ""),
                        "page_count": file_metadata.get("page_count", 0),
                        "is_continuation": chunk_index > 0,
                        "total_section_chunks": None
                    },
                    vector_id=unique_id
                ))
                chunk_index += 1
            
            start = end - self.chunk_overlap if end < text_length else text_length
        
        for chunk in chunks:
            chunk.metadata["total_section_chunks"] = len(chunks)
        
        return chunks

    def create_chunks(self, text: str, file_metadata: Dict[str, any]) -> List[Chunk]:
        """Create text chunks using section-based strategy with overlap."""
        all_chunks = []
        
        file_name = file_metadata.get("file_name", "unknown")
        file_metadata = {**file_metadata, 'source': file_name, 'file_name': file_name}
        
        # 1. Create metadata chunks
        if file_metadata.get('title'):
            unique_id = str(uuid.uuid4())
            all_chunks.append(Chunk(
                text=file_metadata['title'].strip(),
                metadata={
                    **{k: v for k, v in file_metadata.items() if k != 'page_markers'},
                    'section': 'Title',
                    'page': 1,
                    'chunk_index': len(all_chunks),
                    'vector_id': unique_id
                },
                vector_id=unique_id
            ))

        if file_metadata.get('author'):
            unique_id = str(uuid.uuid4())
            all_chunks.append(Chunk(
                text=file_metadata['author'].strip(),
                metadata={
                    **{k: v for k, v in file_metadata.items() if k != 'page_markers'},
                    'section': 'Authors',
                    'page': 1,
                    'chunk_index': len(all_chunks),
                    'vector_id': unique_id
                },
                vector_id=unique_id
            ))
        
        if file_metadata.get('keywords'):
            unique_id = str(uuid.uuid4())
            all_chunks.append(Chunk(
                text=file_metadata['keywords'].strip(),
                metadata={
                    **{k: v for k, v in file_metadata.items() if k != 'page_markers'},
                    'section': 'Keywords',
                    'page': 1,
                    'chunk_index': len(all_chunks),
                    'vector_id': unique_id
                },
                vector_id=unique_id
            ))

        # 2. Find all section boundaries
        sections = self.find_all_sections(text)
        
        if not sections:
            # No sections found - treat entire text as "Content"
            logger.warning("⚠️ No sections detected, using entire text as 'Content'")
            section_chunks = self.create_overlapping_chunks(
                text.strip(),
                "Content",
                file_metadata,
                0
            )
            for chunk in section_chunks:
                chunk.metadata['chunk_index'] = len(all_chunks)
                all_chunks.append(chunk)
        else:
            # Process text section by section
            for i in range(len(sections)):
                start_pos, header_end_pos, section_name = sections[i]
                
                # Determine where this section ends
                if i < len(sections) - 1:
                    end_pos = sections[i + 1][0]  # Start of next section
                else:
                    end_pos = len(text)  # End of document
                
                # Extract section content (skip the header itself)
                section_text = text[header_end_pos:end_pos].strip()
                
                if section_text and len(section_text) > 50:  # Only process substantial content
                    section_chunks = self.create_overlapping_chunks(
                        section_text,
                        section_name,
                        file_metadata,
                        header_end_pos
                    )
                    
                    for chunk in section_chunks:
                        chunk.metadata['chunk_index'] = len(all_chunks)
                        all_chunks.append(chunk)
                    
                    logger.info(f"✅ '{section_name}': {len(section_text)} chars → {len(section_chunks)} chunks")

        sections_found = set(chunk.metadata['section'] for chunk in all_chunks)
        logger.info(f"📊 Created {len(all_chunks)} chunks across {len(sections_found)} sections: {', '.join(sorted(sections_found))}")
        
        return all_chunks

    def process_pdf(self, file_path: str) -> List[Chunk]:
        """Extract text and create chunks from a single PDF."""
        logger.info(f"📖 Processing PDF: {os.path.basename(file_path)}")
        text, metadata = self.extract_text_from_pdf(file_path)
        
        if not text:
            logger.warning(f"⚠️ No text extracted from {file_path}")
            return []
        
        return self.create_chunks(text, metadata)

    def process_pdf_bytes(self, pdf_bytes: bytes, file_name: str = "uploaded.pdf") -> List[Chunk]:
        """Extract text and create chunks from PDF bytes (for uploads)."""
        logger.info(f"📖 Processing uploaded PDF: {file_name}")
        text, metadata = self.extract_text_from_bytes(pdf_bytes, file_name)
        
        if not text:
            logger.warning(f"⚠️ No text extracted from uploaded PDF")
            return []
        
        return self.create_chunks(text, metadata)

    def process_directory(self, directory_path: str) -> List[Chunk]:
        """Process all PDFs in a directory."""
        all_chunks = []
        pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
        
        logger.info(f"📁 Found {len(pdf_files)} PDF files in {directory_path}")
        
        for filename in pdf_files:
            file_path = os.path.join(directory_path, filename)
            try:
                chunks = self.process_pdf(file_path)
                all_chunks.extend(chunks)
                logger.info(f"✅ {filename}: {len(chunks)} chunks created")
            except Exception as e:
                logger.error(f"❌ Error processing {filename}: {str(e)}")
        
        logger.info(f"🎉 Total chunks from all files: {len(all_chunks)}")
        return all_chunks