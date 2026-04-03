"""
Retrieve RAG context from a local Chroma index for appeal drafting.

Uses the same embedding model as ``ingest`` (sentence-transformers). No outbound
network calls; failures degrade to an empty string so drafting can continue.

**Read order matches ``build_denial_guidance_context``:** availability check first,
then ``retrieve_context_for_claim`` (same order as the ``if is_knowledge_base_available()`` branch).
"""
from __future__ import annotations

from dotenv import load_dotenv

from config.logging import get_logger
from config.settings import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR, TOP_K
from utils.e2e_step import e2e_step, preview_text
from utils.error_support import (
    RESOLUTION_CHROMA_QUERY_FAILED,
    RESOLUTION_CHROMA_UNAVAILABLE,
    RESOLUTION_EMBEDDING_MODEL_FAILED,
    format_resolution_for_log,
)

logger = get_logger("knowledge_base.retrieve")

# Ensure .env is applied when RAG runs outside Streamlit (e.g. tests) or before app load_dotenv order changes.
load_dotenv()

# --- Step 1: lightweight gate (runs before query in the guidance path) ---


def is_knowledge_base_available() -> bool:
    """
    Return whether the Chroma directory exists and the collection can be opened.

    Returns
    -------
    bool
        ``True`` if a query is likely to succeed; ``False`` on missing deps or DB.
    """
    with e2e_step(
        logger,
        "knowledge_base.retrieve.is_knowledge_base_available",
        chroma_dir=str(CHROMA_PERSIST_DIR),
    ) as step_trace:
        if not CHROMA_PERSIST_DIR.is_dir():
            step_trace.add(result="false_no_directory")
            return False
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=str(CHROMA_PERSIST_DIR), settings=Settings(anonymized_telemetry=False)
            )
            client.get_collection(CHROMA_COLLECTION_NAME)
            step_trace.add(result="true_collection_opened")
            return True
        except Exception as err:
            logger.warning(
                "Knowledge base availability check failed: %s. action=%s",
                err,
                format_resolution_for_log(RESOLUTION_CHROMA_QUERY_FAILED),
            )
            step_trace.add(result="false_error", error=type(err).__name__)
            return False


# --- Step 2: embed query + fetch chunks (runs only when Step 1 is true) ---


def retrieve_context_for_claim(claim_data: dict, top_k: int = TOP_K) -> str:
    """
    Embed a query built from claim fields and return top matching chunk text.

    Parameters
    ----------
    claim_data :
        Dict with optional payer, denial_code, cpt_code, icd_code, denial_reason.
    top_k :
        Maximum chunks to retrieve (capped at 20 inside the query).

    Returns
    -------
    str
        Joined excerpts with source metadata lines, or ``""`` if Chroma/embeddings
        are unavailable or the index is empty.

    Notes
    -----
    Logs query **structure** (which fields present, character lengths) without
    logging full free-text fields that may contain PHI (e.g. denial_reason text).
    Chunk text previews are reference KB excerpts (curated content), truncated.
    """
    payer = (claim_data.get("payer") or "").strip()
    denial_code = (claim_data.get("denial_code") or "").strip()
    cpt_code = (claim_data.get("cpt_code") or "").strip()
    icd_code = (claim_data.get("icd_code") or "").strip()
    denial_reason = (claim_data.get("denial_reason") or "").strip()

    with e2e_step(
        logger,
        "knowledge_base.retrieve.retrieve_context_for_claim",
        top_k_requested=top_k,
        chroma_dir=str(CHROMA_PERSIST_DIR),
        collection=CHROMA_COLLECTION_NAME,
    ) as step_trace:
        step_trace.add(
            query_field_payer=bool(payer),
            query_field_denial_code=bool(denial_code),
            query_field_cpt=bool(cpt_code),
            query_field_icd=bool(icd_code),
            query_field_denial_reason=bool(denial_reason),
            denial_reason_chars=len(denial_reason) if denial_reason else 0,
        )

        query_parts: list[str] = []
        if payer:
            query_parts.append(payer)
        if denial_code:
            query_parts.append(f"denial code {denial_code}")
        if cpt_code:
            query_parts.append(f"CPT {cpt_code}")
        if icd_code:
            query_parts.append(f"ICD {icd_code}")
        if denial_reason:
            query_parts.append(denial_reason)
        query_parts.append("appeal medical necessity authorization coverage policy guideline")
        query_text = " ".join(query_parts).strip()
        step_trace.add(query_total_chars=len(query_text))

        if not query_text:
            step_trace.add(result="empty_query")
            return ""

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
        except ImportError as err:
            logger.warning(
                "RAG skipped: missing dependency %s. action=%s",
                type(err).__name__,
                format_resolution_for_log(RESOLUTION_CHROMA_UNAVAILABLE),
            )
            step_trace.add(result="missing_optional_dependency", dependency_error=type(err).__name__)
            return ""

        if not CHROMA_PERSIST_DIR.is_dir():
            step_trace.add(result="chroma_directory_missing")
            return ""

        try:
            client = chromadb.PersistentClient(
                path=str(CHROMA_PERSIST_DIR), settings=Settings(anonymized_telemetry=False)
            )
            collection = client.get_collection(CHROMA_COLLECTION_NAME)
        except Exception as err:
            logger.exception(
                "Chroma client/collection open failed: %s. action=%s",
                err,
                format_resolution_for_log(RESOLUTION_CHROMA_QUERY_FAILED),
            )
            step_trace.add(result="chroma_open_failed", error=type(err).__name__)
            return ""

        with e2e_step(logger, "knowledge_base.retrieve.embed_and_query", n_results_cap=min(top_k, 20)) as embed_step:
            try:
                model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as err:
                logger.exception(
                    "SentenceTransformer load failed. action=%s",
                    format_resolution_for_log(RESOLUTION_EMBEDDING_MODEL_FAILED),
                )
                embed_step.add(result="embedding_model_load_failed", error=type(err).__name__)
                step_trace.add(result="rag_embed_model_failed")
                return ""
            embed_step.add(embedding_model="all-MiniLM-L6-v2")
            try:
                query_embedding = model.encode([query_text]).tolist()
            except Exception as err:
                logger.exception(
                    "Sentence encoding failed. action=%s",
                    format_resolution_for_log(RESOLUTION_EMBEDDING_MODEL_FAILED),
                )
                embed_step.add(result="embedding_encode_failed", error=type(err).__name__)
                step_trace.add(result="rag_encode_failed")
                return ""
            n_results = min(top_k, 20)
            try:
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=n_results,
                    include=["documents", "metadatas"],
                )
            except Exception as err:
                logger.exception(
                    "Chroma query failed. action=%s",
                    format_resolution_for_log(RESOLUTION_CHROMA_QUERY_FAILED),
                )
                embed_step.add(result="chroma_query_exception", error=type(err).__name__)
                step_trace.add(result="rag_query_failed")
                return ""
            embed_step.add(chunks_requested=n_results)

        if not results or not results.get("documents") or not results["documents"][0]:
            step_trace.add(result="chroma_query_empty")
            return ""

        docs = results["documents"][0]
        metadatas = (results.get("metadatas") or [[]])[0]
        rag_context_blocks: list[str] = []
        chunk_summaries: list[str] = []
        for chunk_index, doc in enumerate(docs):
            meta = metadatas[chunk_index] if chunk_index < len(metadatas) else {}
            source = meta.get("source", "knowledge base")
            payer_tag = meta.get("payer", "")
            category = meta.get("category", "")
            block_parts = [doc]
            if payer_tag or category:
                source_tail = f"[Source: {source}"
                if category:
                    source_tail += f", {category}"
                if payer_tag:
                    source_tail += f", payor: {payer_tag}"
                source_tail += "]"
                block_parts.append(source_tail)
            block = "\n".join(block_parts)
            rag_context_blocks.append(block)
            chunk_summaries.append(
                f"idx={chunk_index} chars={len(doc)} source={source!r} category={category!r} "
                f"preview={preview_text(doc, 220)!r}"
            )

        joined = "\n\n---\n\n".join(rag_context_blocks)
        step_trace.add(
            result="chunks_retrieved",
            chunks_returned=len(docs),
            total_output_chars=len(joined),
            chunk_details=" | ".join(chunk_summaries),
        )
        return joined
