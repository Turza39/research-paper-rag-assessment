# Technical Approach

This document outlines the key technical decisions and implementation details of the Research Paper RAG System.

## Chunking Strategy

We use a section-aware chunking strategy that:
1. Identifies major paper sections (Abstract, Introduction, Methods, Results, etc.)
2. Preserves semantic context within sections
3. Uses overlapping chunks to maintain context across chunk boundaries
4. Keeps references to page numbers for citation purposes

## Embedding Model Choice

We use the `sentence-transformers/all-mpnet-base-v2` model because:
- Strong performance on academic text
- Good balance of speed and accuracy
- Suitable vector dimensionality for Qdrant
- Proven effectiveness in similar applications

## Prompt Engineering Approach

Our RAG system uses a two-stage prompting strategy:
1. Context Selection
   - Query understanding
   - Relevant chunk retrieval
   - Context ordering and filtering

2. Response Generation
   - Context integration
   - Citation preservation
   - Response structuring

## Database Schema Design

### Paper Metadata
```sql
CREATE TABLE papers (
    id UUID PRIMARY KEY,
    title TEXT,
    authors TEXT[],
    year INTEGER,
    abstract TEXT,
    page_count INTEGER,
    upload_date TIMESTAMP
);
```

### Sections
```sql
CREATE TABLE sections (
    id UUID PRIMARY KEY,
    paper_id UUID REFERENCES papers(id),
    name TEXT,
    content TEXT,
    start_page INTEGER,
    end_page INTEGER
);
```

## Trade-offs and Limitations

1. Text Extraction
   - PDF parsing can be imperfect
   - Complex mathematical formulas may not be preserved
   - Tables and figures are handled as text

2. Chunking
   - Fixed chunk size vs. semantic boundaries
   - Overlap size affects storage requirements
   - Section detection may miss unconventional formats

3. Query Processing
   - Limited to text-based queries
   - May not capture complex relationships
   - Context window size limitations

4. Performance
   - Processing time scales with paper size
   - Vector search speed vs. accuracy trade-off
   - Memory usage during batch processing