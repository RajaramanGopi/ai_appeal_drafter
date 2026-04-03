"""
Ingest curated markdown/JSON and optional URLs into Chroma.
Uses sentence-transformers (local) for embeddings.

URL fetching is restricted (HTTPS, non-private IPs, optional host allowlist)
to reduce SSRF risk when sources.txt lists untrusted input. Per-request HTTP timeout
comes from ``INGEST_URL_REQUEST_TIMEOUT_SECONDS`` in ``config.settings`` (env override).

**File order = pipeline order (Step 0 → Step N):** build the document list and chunking
helpers first; ``run_ingest`` is the **final** step that loads those payloads into Chroma.
**Entry point:** ``run_ingest()`` (or this module's ``__main__``) still *calls* that last
function—it is defined last here so reading top-to-bottom matches "prepare data, then ingest."
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

from config.logging import configure_logging, get_logger
from config.settings import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CHUNK_TOKEN_OVERLAP,
    CHUNK_TOKEN_SIZE,
    DENIAL_CATEGORIES_DIR,
    EMBEDDING_BATCH_SIZE,
    GUIDELINES_DIR,
    INGEST_URL_HOST_ALLOWLIST,
    INGEST_URL_REQUEST_TIMEOUT_SECONDS,
    PAYORS_DIR,
    SOURCES_FILE,
)

logger = get_logger("knowledge_base.ingest")

# --- Step 0: module constants ---

_MAX_URL_RESPONSE_BYTES = 2_000_000


# --- Step 1–3: curated documents (load files, then merge into one list) ---


def _load_curated_markdown(dir_path: str, default_source: str, default_category: str):
    documents = []
    if not os.path.isdir(dir_path):
        return documents
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(dir_path, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as file_handle:
                content = file_handle.read()
        except OSError as err:
            logger.warning("Curated markdown read failed path=%s error=%s", path, err)
            continue
        meta = {"source": default_source, "category": default_category, "title": Path(name).stem}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                except ImportError:
                    logger.warning("PyYAML not installed; skipping front matter for %s", path)
                else:
                    try:
                        meta.update(yaml.safe_load(parts[1]) or {})
                    except yaml.YAMLError as err:
                        logger.warning("Invalid YAML front matter in %s: %s", path, err)
                content = parts[2].strip()
        meta = {k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in meta.items()}
        tag = Path(name).stem
        if default_category == "payor":
            meta["payer"] = tag
        documents.append({"content": content, "metadata": meta})
    return documents


def _load_curated_json(dir_path: str, default_source: str):
    documents = []
    if not os.path.isdir(dir_path):
        return documents
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(dir_path, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as file_handle:
                data = json.load(file_handle)
        except OSError as err:
            logger.warning("Curated JSON read failed path=%s error=%s", path, err)
            continue
        except json.JSONDecodeError as err:
            logger.warning("Curated JSON invalid path=%s error=%s", path, err)
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("content"):
                    item_meta = item.get("metadata") or {}
                    if "source" not in item_meta:
                        item_meta["source"] = default_source
                    documents.append({"content": item["content"], "metadata": item_meta})
        elif isinstance(data, dict) and data.get("content"):
            meta = data.get("metadata") or {}
            if "source" not in meta:
                meta["source"] = default_source
            documents.append({"content": data["content"], "metadata": meta})
    return documents


def _expand_curated():
    payor_md = _load_curated_markdown(str(PAYORS_DIR), "curated", "payor")
    guideline_md = _load_curated_markdown(str(GUIDELINES_DIR), "curated", "guideline")
    denial_md = _load_curated_markdown(str(DENIAL_CATEGORIES_DIR), "curated", "denial_category")
    payor_json = _load_curated_json(str(PAYORS_DIR), "curated")
    guideline_json = _load_curated_json(str(GUIDELINES_DIR), "curated")
    denial_json = _load_curated_json(str(DENIAL_CATEGORIES_DIR), "curated")
    all_docs = payor_md + guideline_md + denial_md + payor_json + guideline_json + denial_json
    logger.info(
        "Curated KB documents loaded: payor_md=%d guideline_md=%d denial_md=%d "
        "payor_json=%d guideline_json=%d denial_json=%d total_documents=%d",
        len(payor_md),
        len(guideline_md),
        len(denial_md),
        len(payor_json),
        len(guideline_json),
        len(denial_json),
        len(all_docs),
    )
    if not os.path.isdir(str(PAYORS_DIR)):
        logger.warning("Payors curated directory missing or not a directory: %s", PAYORS_DIR)
    if not os.path.isdir(str(GUIDELINES_DIR)):
        logger.warning("Guidelines curated directory missing or not a directory: %s", GUIDELINES_DIR)
    if not os.path.isdir(str(DENIAL_CATEGORIES_DIR)):
        logger.warning(
            "Denial categories curated directory missing or not a directory: %s",
            DENIAL_CATEGORIES_DIR,
        )
    return all_docs


# --- Step 4–6: optional URL sources (policy → fetch) ---


def _host_matches_allowlist(host: str) -> bool:
    if not INGEST_URL_HOST_ALLOWLIST:
        return True
    normalized_host = (host or "").lower().rstrip(".")
    for allowed_host in INGEST_URL_HOST_ALLOWLIST:
        allowed_normalized = allowed_host.lower().rstrip(".")
        if normalized_host == allowed_normalized or normalized_host.endswith("." + allowed_normalized):
            return True
    return False


def _is_safe_public_https_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        return False
    host = parsed.hostname
    if not host or not _host_matches_allowlist(host):
        return False
    try:
        address_infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in address_infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not ip.is_global:
            return False
    return bool(address_infos)


def _optional_fetch_urls():
    docs = []
    if not SOURCES_FILE.is_file():
        logger.info("URL ingest skipped: sources file not found at %s", SOURCES_FILE)
        return docs
    try:
        import requests
        import trafilatura
    except ImportError as err:
        logger.error(
            "URL ingest skipped: missing dependency %s. Install with: pip install requests trafilatura",
            err,
        )
        return docs
    with open(SOURCES_FILE, encoding="utf-8", errors="replace") as file_handle:
        urls = [
            line.strip()
            for line in file_handle
            if line.strip() and not line.strip().startswith("#")
        ]
    logger.info(
        "URL ingest: %d non-comment URL(s) listed in %s timeout_seconds=%s allowlist_configured=%s",
        len(urls),
        SOURCES_FILE,
        INGEST_URL_REQUEST_TIMEOUT_SECONDS,
        bool(INGEST_URL_HOST_ALLOWLIST),
    )
    skipped_policy = 0
    skipped_redirect = 0
    fetch_errors = 0
    empty_extract = 0
    for url in urls:
        if not _is_safe_public_https_url(url):
            skipped_policy += 1
            logger.warning(
                "URL skipped (HTTPS/public-IP/allowlist policy): %s — adjust URL or INGEST_URL_HOST_ALLOWLIST",
                url[:200],
            )
            continue
        logger.info("URL fetch start: %s", url[:500])
        try:
            with requests.get(
                url,
                timeout=INGEST_URL_REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": "AppealDrafterKB/1.0"},
                stream=True,
                allow_redirects=True,
            ) as resp:
                final_url = (resp.url or url).strip()
                if not _is_safe_public_https_url(final_url):
                    skipped_redirect += 1
                    logger.warning(
                        "URL skipped after redirect (safety check failed): initial=%s final=%s",
                        url[:200],
                        final_url[:200],
                    )
                    continue
                resp.raise_for_status()
                encoding = resp.encoding or "utf-8"
                raw = b""
                for response_chunk in resp.iter_content(chunk_size=65536):
                    if not response_chunk:
                        continue
                    raw += response_chunk
                    if len(raw) > _MAX_URL_RESPONSE_BYTES:
                        logger.warning(
                            "URL response truncated at %d bytes: %s",
                            _MAX_URL_RESPONSE_BYTES,
                            url[:200],
                        )
                        break
            text = raw.decode(encoding, errors="replace")
            extracted = trafilatura.extract(
                text, include_comments=False, include_tables=True, output_format="markdown"
            )
            if extracted and extracted.strip():
                char_count = len(extracted.strip())
                docs.append(
                    {
                        "content": extracted,
                        "metadata": {"source": "url", "url": url, "category": "policy"},
                    }
                )
                logger.info(
                    "URL fetch OK: extracted_markdown_chars=%d status_line=%s final_url=%s",
                    char_count,
                    getattr(resp, "status_code", "?"),
                    final_url[:300],
                )
            else:
                empty_extract += 1
                logger.warning(
                    "URL fetch OK but no text extracted (HTML may be empty or trafilatura found nothing): %s",
                    url[:300],
                )
        except requests.RequestException as err:
            fetch_errors += 1
            logger.warning(
                "URL fetch failed: url=%s error_type=%s error=%s — check network, TLS, and site availability",
                url[:300],
                type(err).__name__,
                err,
            )
        except Exception as err:
            fetch_errors += 1
            logger.warning(
                "URL ingest failed: url=%s error_type=%s error=%s",
                url[:300],
                type(err).__name__,
                err,
            )
    logger.info(
        "URL ingest summary: documents_added=%d skipped_policy=%d skipped_redirect=%d "
        "fetch_or_parse_errors=%d empty_extraction=%d",
        len(docs),
        skipped_policy,
        skipped_redirect,
        fetch_errors,
        empty_extract,
    )
    return docs


# --- Step 7: split text by tokenizer windows (token-size chunks) ---


def _chunk_text_with_tokenizer(
    text: str,
    tokenizer: Any,
    chunk_token_size: int = CHUNK_TOKEN_SIZE,
    token_overlap: int = CHUNK_TOKEN_OVERLAP,
) -> list[str]:
    if not text or not text.strip():
        return []
    if chunk_token_size <= 0:
        raise ValueError("chunk_token_size must be > 0")
    if token_overlap < 0:
        raise ValueError("token_overlap must be >= 0")
    if token_overlap >= chunk_token_size:
        raise ValueError("token_overlap must be smaller than chunk_token_size")

    token_ids = tokenizer.encode(text.strip(), add_special_tokens=False)
    if not token_ids:
        return []

    stride = chunk_token_size - token_overlap
    chunks: list[str] = []
    start = 0
    while start < len(token_ids):
        end = min(start + chunk_token_size, len(token_ids))
        chunk_ids = token_ids[start:end]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True).strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end >= len(token_ids):
            break
        start += stride
    return chunks


# --- Step 8: embedding helper (explicit batching) ---


def _encode_embeddings_in_batches(
    model: Any,
    texts: list[str],
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    all_vectors: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    for batch_index, start in enumerate(range(0, len(texts), batch_size), start=1):
        end = min(start + batch_size, len(texts))
        batch = texts[start:end]
        logger.info(
            "Embedding batch start: batch=%d/%d size=%d",
            batch_index,
            total_batches,
            len(batch),
        )
        vectors = model.encode(batch, batch_size=len(batch), show_progress_bar=False).tolist()
        all_vectors.extend(vectors)
    return all_vectors


# --- Step 9: orchestration — collect Steps 1–7, embed, write Chroma (runs last in the pipeline) ---


def run_ingest(use_urls: bool = False):
    # Load .env so HF_TOKEN (optional) is set before sentence-transformers hits the Hub.
    load_dotenv()
    logger.info(
        "Ingest run start: use_urls=%s chroma_dir=%s collection=%s token_chunk_size=%d token_overlap=%d embedding_batch_size=%d",
        use_urls,
        CHROMA_PERSIST_DIR,
        CHROMA_COLLECTION_NAME,
        CHUNK_TOKEN_SIZE,
        CHUNK_TOKEN_OVERLAP,
        EMBEDDING_BATCH_SIZE,
    )
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as err:
        logger.error(
            "Ingest aborted: sentence-transformers not installed. Run: pip install sentence-transformers"
        )
        raise ImportError("Install sentence-transformers: pip install sentence-transformers") from err

    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as err:
        logger.error("Ingest aborted: chromadb not installed. Run: pip install chromadb")
        raise ImportError("Install chromadb: pip install chromadb") from err

    documents = _expand_curated()
    if use_urls:
        url_docs = _optional_fetch_urls()
        documents.extend(url_docs)
        logger.info("After URL ingest: total_documents=%d (added_from_urls=%d)", len(documents), len(url_docs))
    else:
        logger.info("URL ingest not requested (--urls omitted); curated documents only: count=%d", len(documents))

    if not documents:
        logger.warning(
            "Ingest finished with 0 documents — nothing to embed. Add curated .md under knowledge_base/curated/ "
            "and/or enable --urls with valid entries in knowledge_base/sources.txt"
        )
        return 0

    logger.info("Loading embedding model (first run may download weights)...")
    if not (os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")):
        logger.info(
            "HF_TOKEN not set: Hugging Face Hub may show a rate-limit notice. "
            "Add HF_TOKEN to .env for authenticated downloads (see .env.example)."
        )
    model = SentenceTransformer("all-MiniLM-L6-v2")
    tokenizer = getattr(model, "tokenizer", None)
    if tokenizer is None:
        raise RuntimeError("Embedding model tokenizer unavailable; cannot perform token-based chunking.")

    ids = []
    texts = []
    metadatas = []
    # IDs must be unique across all chunks. Do not hash only content[:100] + chunk_index — many URL-ingested
    # documents share identical boilerplate, which produced DuplicateIDError in Chroma.
    for doc_index, doc in enumerate(documents):
        content = doc["content"]
        meta = doc.get("metadata") or {}
        for chunk_index, chunk in enumerate(_chunk_text_with_tokenizer(content, tokenizer)):
            chunk_id = hashlib.sha256(
                f"{doc_index}:{chunk_index}:{chunk}".encode("utf-8", errors="replace")
            ).hexdigest()[:32]
            ids.append(chunk_id)
            texts.append(chunk)
            chunk_metadata = {
                key: (value if isinstance(value, (str, int, float, bool)) else str(value))
                for key, value in meta.items()
            }
            chunk_metadata["chunk_index"] = chunk_index
            chunk_metadata["source_doc_index"] = doc_index
            metadatas.append(chunk_metadata)

    if not texts:
        logger.warning("Ingest produced 0 chunks (all document bodies empty after trim); check source files")
        return 0

    logger.info(
        "Token chunking complete: total_chunks=%d from_documents=%d (embedding_model=all-MiniLM-L6-v2)",
        len(texts),
        len(documents),
    )
    logger.info("Encoding %d chunk(s) into embeddings with batch_size=%d...", len(texts), EMBEDDING_BATCH_SIZE)
    embeddings = _encode_embeddings_in_batches(model, texts, batch_size=EMBEDDING_BATCH_SIZE)
    logger.info("Embedding encode complete: vector_count=%d", len(embeddings))

    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Chroma persist directory ready: %s", CHROMA_PERSIST_DIR)
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR), settings=Settings(anonymized_telemetry=False)
    )
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        logger.info("Removed existing Chroma collection %r for full rebuild", CHROMA_COLLECTION_NAME)
    except Exception as err:
        logger.info(
            "No existing collection to delete (or delete failed — continuing): collection=%r detail=%s",
            CHROMA_COLLECTION_NAME,
            err,
        )
    collection = client.create_collection(name=CHROMA_COLLECTION_NAME, metadata={"description": "Appeal knowledge base"})
    logger.info("Created Chroma collection %r", CHROMA_COLLECTION_NAME)

    batch_size = 100
    batch_count = (len(ids) + batch_size - 1) // batch_size
    for batch_index, batch_start in enumerate(range(0, len(ids), batch_size), start=1):
        batch_end = min(batch_start + batch_size, len(ids))
        collection.add(
            ids=ids[batch_start:batch_end],
            embeddings=embeddings[batch_start:batch_end],
            documents=texts[batch_start:batch_end],
            metadatas=metadatas[batch_start:batch_end],
        )
        logger.info(
            "Chroma batch written: batch=%d/%d ids=%d..%d size=%d",
            batch_index,
            batch_count,
            batch_start,
            batch_end - 1,
            batch_end - batch_start,
        )
    logger.info(
        "Ingest run complete: chunks_written=%d collection=%r path=%s",
        len(ids),
        CHROMA_COLLECTION_NAME,
        CHROMA_PERSIST_DIR,
    )
    return len(ids)


# --- Step 10: CLI entry ---

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Build or rebuild the Appeal Drafter Chroma knowledge index.")
    parser.add_argument(
        "--urls",
        action="store_true",
        help="Also fetch and ingest HTTPS URLs from knowledge_base/sources.txt",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging for appeal_ai loggers",
    )
    args = parser.parse_args()

    import logging

    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(level=log_level, log_to_file=True)
    if args.verbose:
        logging.getLogger("appeal_ai").setLevel(logging.DEBUG)

    logger.info(
        "CLI ingest invoked argv=%s use_urls=%s log_level=%s",
        sys.argv,
        args.urls,
        logging.getLevelName(log_level),
    )
    try:
        n_chunks = run_ingest(use_urls=args.urls)
    except Exception:
        logger.exception(
            "CLI ingest failed — see traceback above. Typical fixes: install deps from requirements.txt, "
            "ensure curated files exist under knowledge_base/curated/, and check disk space for chroma_db."
        )
        raise
    print(f"Ingested {n_chunks} chunks into Chroma at {CHROMA_PERSIST_DIR}")
    logger.info("CLI ingest exit OK chunks=%d", n_chunks)
