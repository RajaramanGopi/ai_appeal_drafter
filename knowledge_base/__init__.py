"""
Knowledge base for Appeal Drafter AI: ingest curated content (and optional URLs),
embed with sentence-transformers, store in Chroma, and retrieve for RAG.
"""
from knowledge_base.retrieve import retrieve_context_for_claim

__all__ = ["retrieve_context_for_claim"]
