# """
# Service for processing PDF files with intelligent chunking and metadata extraction.
# """
# import os
# import re
# import logging
# from typing import Dict, List, Tuple, Optional
# from datetime import datetime
# from PyPDF2 import PdfReader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from src.models.paper import Paper, Section, Chunk

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class PDFProcessor:
#     def __init__(self):
#         """Initialize with intelligent chunking strategy."""
#         self.text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=500,
#             chunk_overlap=50,
#             length_function=len,
#             separators=[
#                 "\n## ",      # Section headers
#                 "\n\n",       # Paragraphs
#                 ".\n",        # Sentence with newline
#                 ". ",         # Sentence
#                 "?\n",        # Question with newline
#                 "? ",         # Question
#                 "\n",         # Newlines
#                 " ",          # Spaces
#                 ""           # Characters
#             ]
#         )

#     def extract_metadata(self, pdf_reader: PdfReader, file_path: str) -> Dict[str, any]:
#         """Extract comprehensive metadata from PDF."""
#         metadata = {
#             'file_path': file_path,
#             'filename': os.path.basename(file_path),
#             'page_count': len(pdf_reader.pages),
#             'processed_date': datetime.utcnow()
#         }

#         # Extract PDF metadata if available
#         if pdf_reader.metadata:
#             metadata.update({
#                 'title': pdf_reader.metadata.get('/Title', '').strip(),
#                 'authors': [a.strip() for a in pdf_reader.metadata.get('/Author', '').split(',') if a.strip()],
#                 'subject': pdf_reader.metadata.get('/Subject', '').strip(),
#                 'keywords': [k.strip() for k in pdf_reader.metadata.get('/Keywords', '').split(',') if k.strip()]
#             })

#         return metadata

#     def identify_sections(self, text: str) -> Dict[str, Tuple[str, int, int]]:
#         """Identify paper sections and their page ranges."""
#         sections = {}
#         current_section = None
#         current_content = []
#         current_start_page = 1
#         current_page = 1

#         # Common section headers in research papers
#         section_patterns = [
#             r'abstract',
#             r'introduction',
#             r'background',
#             r'related work',
#             r'methodology|methods',
#             r'experimental setup|experiments',
#             r'results|findings',
#             r'discussion',
#             r'conclusion',
#             r'future work',
#             r'references'
#         ]
#         section_re = re.compile(r'\n(' + '|'.join(section_patterns) + r')\s*\n', re.IGNORECASE)

#         # Process text line by line
#         for line in text.split('\n'):
#             # Check for page markers
#             page_match = re.match(r'## Page (\d+)', line)
#             if page_match:
#                 current_page = int(page_match.group(1))
#                 continue

#             # Check for section headers
#             if section_re.search(f"\n{line}\n"):
#                 # Store previous section if it exists
#                 if current_section:
#                     sections[current_section] = ('\n'.join(current_content).strip(),
#                                               current_start_page,
#                                               current_page)
                
#                 current_section = line.strip().lower()
#                 current_content = []
#                 current_start_page = current_page
#             elif current_section:
#                 current_content.append(line)

#         # Store last section
#         if current_section and current_content:
#             sections[current_section] = ('\n'.join(current_content).strip(),
#                                       current_start_page,
#                                       current_page)

#         return sections

#     def create_chunks(self, section: Section, paper_metadata: Dict[str, any]) -> List[Dict]:
#         """Create chunks from a section with metadata."""
#         chunks = []
        
#         # Split section content into chunks
#         text_chunks = self.text_splitter.split_text(section.content)
        
#         # Create chunk objects with metadata
#         for i, chunk_text in enumerate(text_chunks):
#             chunk = {
#                 'text': chunk_text,
#                 'metadata': {
#                     'paper_title': paper_metadata.get('title'),
#                     'paper_path': paper_metadata.get('file_path'),
#                     'section': section.title,
#                     'page_start': section.page_start,
#                     'page_end': section.page_end,
#                     'chunk_index': i,
#                     'total_chunks': len(text_chunks)
#                 }
#             }
#             chunks.append(chunk)
        
#         return chunks

#     def process_pdf(self, file_path: str) -> Tuple[Paper, List[Dict]]:
#         """Process PDF into structured Paper object with sections and chunks."""
#         logger.info(f"Processing PDF: {os.path.basename(file_path)}")
        
#         try:
#             with open(file_path, 'rb') as file:
#                 pdf = PdfReader(file)
#                 metadata = self.extract_metadata(pdf, file_path)
                
#                 # Extract text with page numbers
#                 full_text = ""
#                 for i, page in enumerate(pdf.pages, 1):
#                     text = page.extract_text()
#                     if text:
#                         full_text += f"\n## Page {i}\n\n{text}\n\n"
                
#                 # Identify sections
#                 sections_data = self.identify_sections(full_text)
                
#                 # Convert to Section objects
#                 sections = {}
#                 for title, (content, start_page, end_page) in sections_data.items():
#                     sections[title] = Section(
#                         title=title,
#                         content=content,
#                         page_start=start_page,
#                         page_end=end_page,
#                         vector_ids=[]
#                     )
                
#                 # Create Paper object
#                 paper = Paper(
#                     title=metadata.get('title', 'Untitled'),
#                     authors=metadata.get('authors', []),
#                     year=None,  # Can be extracted from text or metadata
#                     abstract=sections.get('abstract', Section(
#                         title='abstract',
#                         content='',
#                         page_start=1,
#                         page_end=1,
#                         vector_ids=[]
#                     )).content,
#                     sections=sections,
#                     file_path=file_path,
#                     page_count=metadata['page_count'],
#                     metadata=metadata
#                 )
                
#                 logger.info(f"Successfully processed paper: {paper.title}")
#                 return paper
                
#         except Exception as e:
#             logger.error(f"Error processing PDF {file_path}: {str(e)}")
#             raise
#         with open(file_path, 'rb') as file:
#             pdf = PdfReader(file)
#             text = ""
#             metadata = {
#                 'page_count': len(pdf.pages),
#                 'file_name': os.path.basename(file_path),
#                 'title': '',
#                 'author': '',
#                 'keywords': ''
#             }

#             for i, page in enumerate(pdf.pages):
#                 page_text = page.extract_text()
#                 if page_text:
#                     text += f"\n## Page {i+1}\n\n{page_text}\n\n"

#             # Extract PDF metadata
#             if pdf.metadata:
#                 metadata.update({
#                     'title': pdf.metadata.get('/Title', '').strip(),
#                     'author': pdf.metadata.get('/Author', '').strip(),
#                     'keywords': pdf.metadata.get('/Keywords', '').strip()
#                 })

#             # Fallback to first page if metadata missing
#             if not metadata['title'] or not metadata['author']:
#                 first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
#                 lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
#                 if not metadata['title'] and lines:
#                     metadata['title'] = lines[0]
#                 if not metadata['author'] and len(lines) > 1:
#                     metadata['author'] = lines[1]

#         return text, metadata

#     def create_chunks(self, text: str, file_metadata: Dict[str, any], max_chunk_size: int = 1000) -> List[Chunk]:
#         """
#         Create chunks without losing words, preserving sections.
#         """
#         text_chunks = []

#         # Ensure 'source' key exists in metadata
#         file_metadata = {**file_metadata, 'source': file_metadata.get('file_name', 'unknown')}

#         # 1. Handle special sections: Title, Authors, Keywords
#         special_sections = {}
#         if file_metadata.get('title'):
#             special_sections['Title'] = file_metadata['title']
#         if file_metadata.get('author'):
#             special_sections['Authors'] = file_metadata['author']
#         if file_metadata.get('keywords'):
#             special_sections['Keywords'] = file_metadata['keywords']

#         for section_name, section_text in special_sections.items():
#             if section_text.strip():
#                 text_chunks.append(Chunk(
#                     text=section_text.strip(),
#                     metadata={**file_metadata, 'section': section_name, 'chunk_index': len(text_chunks)}
#                 ))

#         # 2. Extract Abstract
#         abstract_match = re.search(r'Abstract[:\s]*(.+?)(?=\n##|\Z)', text, re.IGNORECASE | re.DOTALL)
#         if abstract_match:
#             abstract_text = abstract_match.group(1).strip()
#             text_chunks.append(Chunk(
#                 text=abstract_text,
#                 metadata={**file_metadata, 'section': 'Abstract', 'chunk_index': len(text_chunks)}
#             ))

#         # 3. Split remaining text into paragraphs
#         paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

#         for para in paragraphs:
#             if len(para) <= max_chunk_size:
#                 text_chunks.append(Chunk(
#                     text=para,
#                     metadata={**file_metadata, 'section': 'Paragraph', 'chunk_index': len(text_chunks)}
#                 ))
#             else:
#                 # Split long paragraphs into smaller chunks
#                 start = 0
#                 while start < len(para):
#                     end = min(start + max_chunk_size, len(para))
#                     chunk_text = para[start:end].strip()
#                     text_chunks.append(Chunk(
#                         text=chunk_text,
#                         metadata={**file_metadata, 'section': 'Paragraph', 'chunk_index': len(text_chunks)}
#                     ))
#                     start += max_chunk_size

#         return text_chunks

#     def process_pdf(self, file_path: str) -> List[Chunk]:
#         text, metadata = self.extract_text_from_pdf(file_path)
#         return self.create_chunks(text, metadata)

#     def process_directory(self, directory_path: str) -> List[Chunk]:
#         all_chunks = []
#         for filename in os.listdir(directory_path):
#             if filename.lower().endswith('.pdf'):
#                 file_path = os.path.join(directory_path, filename)
#                 try:
#                     chunks = self.process_pdf(file_path)
#                     all_chunks.extend(chunks)
#                     print(f"Processed {filename}: {len(chunks)} chunks created")
#                 except Exception as e:
#                     print(f"Error processing {filename}: {str(e)}")
#         return all_chunks





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
