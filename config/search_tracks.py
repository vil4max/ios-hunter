"""Deterministic career-search policy; iOS remains the primary track."""

AI_TARGET_TITLES = (
    "Senior Software Engineer + AI", "Applied AI Engineer", "AI Software Engineer",
    "LLM Engineer", "Agentic AI Engineer", "Backend Engineer + AI",
    "AI Platform Engineer", "AI Integration Engineer", "AI Solutions Engineer",
)
AI_SEARCH_KEYWORDS = ("AI", "LLM", "agentic")
AI_RELEVANCE_PATTERNS = {
    "LLM APIs": r"\b(?:llm\s*apis?|openai|anthropic)\b",
    "agents/tool orchestration": r"\b(?:agents?|agentic|tool[ -](?:calling|orchestration)|mcp)\b",
    "RAG": r"\b(?:rag|retrieval[ -]augmented)\b",
    "structured generation": r"\bstructured\s+(?:generation|outputs?)\b",
    "evals": r"\b(?:evals?|evaluations?)\b",
    "observability": r"\bobservability\b",
    "reliability/fallbacks": r"\b(?:reliability|fallbacks?)\b",
    "backend integration": r"\bbackend\s+integration\b",
    "cloud": r"\b(?:cloud|aws|azure|gcp)\b",
    "Docker": r"\bdocker\b",
    "SQL": r"\b(?:sql|postgresql)\b",
}
