"""
Utility functions and constants for research paper RAG system.
Provides helper methods for common operations across services.
"""
from typing import List, Dict, Set, Tuple
import re
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence levels for context-aware responses."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class PaperSection(str, Enum):
    """Standard sections found in research papers."""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    CONCLUSION = "conclusion"
    DISCUSSION = "discussion"
    FUTURE_WORK = "future_work"
    REFERENCES = "references"


# Threshold constants
CONTEXT_SCORE_THRESHOLDS = {
    ConfidenceLevel.HIGH: 0.7,
    ConfidenceLevel.MEDIUM: 0.5,
    ConfidenceLevel.LOW: 0.3,
    ConfidenceLevel.VERY_LOW: 0.0,
}

# Max tokens for different operations
MAX_TOKENS_LIMITS = {
    "summary": 500,
    "abstract": 300,
    "response": 1500,
    "total_context": 6000,
}

# Section keywords for detection
SECTION_KEYWORDS_EXPANDED = {
    PaperSection.ABSTRACT: [
        "abstract", "summary", "overview", "synopsis", "executive summary"
    ],
    PaperSection.INTRODUCTION: [
        "introduction", "intro", "background", "related work", "motivation",
        "problem statement", "context"
    ],
    PaperSection.METHODOLOGY: [
        "methodology", "method", "approach", "framework", "architecture",
        "system design", "implementation", "techniques", "algorithms"
    ],
    PaperSection.RESULTS: [
        "results", "findings", "experiments", "evaluation", "performance",
        "outcomes", "data", "analysis", "metrics", "benchmarks"
    ],
    PaperSection.CONCLUSION: [
        "conclusion", "conclusions", "summary", "final remarks", "concluding",
        "outcome", "takeaway"
    ],
    PaperSection.DISCUSSION: [
        "discussion", "analysis", "implications", "interpretation", "insights",
        "significance", "impact", "findings discuss"
    ],
    PaperSection.FUTURE_WORK: [
        "future work", "future research", "future directions", "limitations",
        "open problems", "challenges", "next steps"
    ],
    PaperSection.REFERENCES: [
        "references", "citations", "bibliography", "works cited", "sources"
    ],
}

# Out-of-context keywords
OUT_OF_CONTEXT_PATTERNS = {
    "greeting": ["hi", "hello", "hey", "greetings", "howdy", "what's up"],
    "casual": [
        "how are you", "how's it going", "thanks", "thank you",
        "appreciate", "good job", "thanks for"
    ],
    "meta": [
        "what can you do", "help", "what is this", "who are you",
        "tell me about yourself", "describe yourself", "capabilities",
        "features", "functions", "what do you do"
    ],
}

# Global operation keywords
GLOBAL_OPERATIONS = {
    "summary": ["summary", "summarize", "summarization", "summed up", "tl;dr"],
    "overview": ["overview", "big picture", "high level", "outline"],
    "translate": ["translate", "translation", "convert", "rephrase"],
    "rewrite": ["rewrite", "rewriting", "paraphrase", "simplify", "explain simply"],
    "bullet": ["bullet", "bullets", "points", "list", "enumerate", "key points"],
    "compare": ["compare", "comparison", "vs", "versus", "difference", "different"],
    "explain": ["explain", "explanation", "clarify", "elaborate", "detail"],
    "extract": ["extract", "pull out", "find", "get", "show me"],
}


def normalize_query(query: str) -> str:
    """Normalize query for consistent processing."""
    # Convert to lowercase
    query = query.lower()
    # Remove extra whitespace
    query = " ".join(query.split())
    # Remove common punctuation
    query = re.sub(r'[?!]+$', '', query)
    return query


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract important keywords from text."""
    # Simple keyword extraction (can be enhanced)
    words = text.lower().split()
    # Filter out common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from'
    }
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    return keywords[:max_keywords]


def calculate_text_similarity_basic(text1: str, text2: str) -> float:
    """Basic text similarity using word overlap."""
    words1 = set(normalize_query(text1).split())
    words2 = set(normalize_query(text2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def chunk_text_by_tokens(text: str, max_tokens: int = 500) -> List[str]:
    """Split text into chunks based on approximate token count."""
    # Rough estimation: 1 token ≈ 4 characters
    chars_per_chunk = max_tokens * 4
    
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < chars_per_chunk:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    # Rough estimation: 1 token ≈ 4 characters
    return len(text) // 4


def merge_citations(citations_list: List[Dict]) -> List[Dict]:
    """Merge and deduplicate citations."""
    seen = {}
    merged = []
    
    for citation in citations_list:
        key = (citation.get("paper_title"), citation.get("section"), citation.get("page"))
        if key not in seen:
            seen[key] = citation
            merged.append(citation)
        else:
            # Update relevance score to max
            seen[key]["relevance_score"] = max(
                seen[key].get("relevance_score", 0.0),
                citation.get("relevance_score", 0.0)
            )
    
    return merged


def format_confidence_display(score: float) -> str:
    """Format confidence score for display."""
    percentage = int(score * 100)
    bar_length = 10
    filled = int(bar_length * score)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"{bar} {percentage}%"


def get_section_emoji(section: str) -> str:
    """Get emoji representation for paper section."""
    emojis = {
        "abstract": "📋",
        "introduction": "📖",
        "methodology": "🔬",
        "results": "📊",
        "conclusion": "✅",
        "discussion": "💬",
        "future_work": "🚀",
        "references": "📚",
    }
    return emojis.get(section.lower(), "📄")


def format_section_name(section: str) -> str:
    """Format section name for display."""
    return section.replace("_", " ").title()


def build_metadata_string(metadata: Dict) -> str:
    """Build readable metadata string."""
    parts = []
    
    if metadata.get("source"):
        parts.append(f"📄 {metadata['source']}")
    if metadata.get("section"):
        section_emoji = get_emoji_for_section(metadata['section'])
        parts.append(f"{section_emoji} {format_section_name(metadata['section'])}")
    if metadata.get("page"):
        parts.append(f"📍 Page {metadata['page']}")
    
    return " | ".join(parts)


def get_emoji_for_section(section: str) -> str:
    """Get emoji for section."""
    section_lower = section.lower()
    emojis = {
        "abstract": "📋",
        "introduction": "📖",
        "methodology": "🔬",
        "results": "📊",
        "conclusion": "✅",
        "discussion": "💬",
        "future_work": "🚀",
        "references": "📚",
    }
    
    for key, emoji in emojis.items():
        if key in section_lower:
            return emoji
    return "📄"


def is_section_match(text: str, section: str) -> bool:
    """Check if text matches a section."""
    section_lower = section.lower()
    text_lower = text.lower()
    
    keywords = SECTION_KEYWORDS_EXPANDED.get(section, [])
    return any(keyword in text_lower for keyword in keywords)


def filter_by_confidence(items: List[Dict], min_score: float = 0.5) -> List[Dict]:
    """Filter items by minimum confidence score."""
    return [
        item for item in items
        if item.get("score", item.get("relevance_score", 0.0)) >= min_score
    ]


def sort_by_score(items: List[Dict], reverse: bool = True) -> List[Dict]:
    """Sort items by score (similarity or relevance)."""
    return sorted(
        items,
        key=lambda x: x.get("score", x.get("relevance_score", 0.0)),
        reverse=reverse
    )


def deduplicate_results(results: List[Dict], key_func=None) -> List[Dict]:
    """Remove duplicate results based on content."""
    if key_func is None:
        key_func = lambda x: x.get("text", "")
    
    seen = set()
    deduplicated = []
    
    for result in results:
        key = key_func(result)
        if key not in seen:
            seen.add(key)
            deduplicated.append(result)
    
    return deduplicated
