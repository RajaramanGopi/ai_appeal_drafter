# Knowledge Base Implementation Plan (Free Tools, MVP)

## Goal

Build a **policy-backed knowledge base** so the AI Appeal Drafter can:
- Generate appeal letters that **reference real policies and guidelines**
- Improve approval chances with **denial-specific and payor-specific guidance**
- Start with **major denial categories, major payors, and key guidelines**, then expand

## Constraints

- **No paid Firecrawl** — use free crawling/curation only
- **Free DB, free APIs** — no paid vector DB or embedding APIs required for MVP
- **MVP first** — working product, then iterate (more denial groups, payors, forms, guidelines)

---

## Free-Tools Stack (Replacements for Paid Services)

| Step | Paid (Original) | Free (This MVP) |
|------|------------------|------------------|
| **Crawl / Ingest** | Firecrawl API | **Trafilatura** (extract main content from URLs), **curated Markdown/JSON** (no crawl for MVP) |
| **Store** | Pinecone / Weaviate | **Chroma** (local, free, persistent) or **SQLite** for metadata |
| **Embeddings** | OpenAI `text-embedding-3-small` | **sentence-transformers** (`all-MiniLM-L6-v2`) — runs locally, no API key |
| **Retrieval** | Vector search in paid DB | **Chroma** similarity search (free) |
| **LLM** | (unchanged) | Your existing OpenAI / Gemini setup |

### Why These Choices

- **Trafilatura**: One of the best open-source article/main-content extractors; no API key; works on CMS, payer policy pages (where not blocked).
- **Chroma**: Embeddings + metadata in one place; persists to disk; simple Python API; no server needed.
- **sentence-transformers**: Free, runs on CPU; good quality for semantic search; no rate limits.

---

## High-Level Architecture (MVP)

```
Curated content (Markdown/JSON) + optional URL fetch (Trafilatura)
        ↓
Chunk (e.g. 500 chars) + tag (payer, denial_category, CPT, guideline_type)
        ↓
Embed with sentence-transformers → Store in Chroma
        ↓
At appeal time: query by denial_code, payer, CPT, denial_reason text
        ↓
Retrieve top-k chunks → Merge with existing CSV denial guidance
        ↓
LLM (OpenAI/Gemini) → Appeal draft
```

---

## MVP Data Scope (Phase 1)

Start with **structured, curated content** so the system works without any crawling:

1. **Major denial categories** (you already have these in `denial_knowledge_base - Main.csv`)
   - Use CSV as-is for exact denial-code lookup.
   - Add **vector index** for the same content so we can also retrieve by **semantic similarity** (e.g. free-text denial reason).

2. **Major payors and standard appeal methods**
   - **Aetna** (you have form) — add: appeal process summary, where to submit, timelines.
   - **UnitedHealthcare (UHC)** — same.
   - **BCBS** — same.
   - **Cigna** — same.
   - **Medicare (CMS)** — same.
   - Store as small markdown or JSON docs per payor (e.g. `knowledge_base/curated/payors/Aetna.md`).

3. **Major guidelines**
   - **CMS**: Coverage basics, medical necessity, NCD/LCD references (short summaries or links).
   - **CPT/ICD**: When to use 99213 vs 99214, common bundling rules (NCCI), documentation requirements.
   - Store as `knowledge_base/curated/guidelines/` (markdown files or JSON).

4. **Payer-specific forms**
   - You already have `payor_standard_appeal_forms/`. No change; the knowledge base can reference “use standard form for Aetna” (already in CSV/UI).

Later (Phase 2+): Add more denial groups, payors, forms, and optional **scheduled Trafilatura runs** on a short list of allowed URLs (e.g. CMS policy pages).

---

## Implementation Steps

### Step 1: Project layout

```
appeal_ai/
  knowledge_base/
    __init__.py
    (see ../config/settings.py for KB paths, chunk size, top_k)
    ingest.py           # load curated + optional URL fetch, chunk, embed, save to Chroma
    retrieve.py         # query by denial_code, payer, CPT, free text → top-k chunks
    curated/            # curated content (no crawl needed for MVP)
      payors/           # Aetna.md, UnitedHealthcare.md, ...
      guidelines/       # cms_coverage.md, cpt_99213_99214.md, ncci_bundling.md, ...
      denial_categories/ # optional: extended denial category notes
    chroma_db/          # Chroma persistence (gitignore or commit empty)
  data/
    denial_knowledge_base - Main.csv   # existing
  ... (rest unchanged)
```

### Step 2: Ingest pipeline

- **Curated**: Read all `knowledge_base/curated/**/*.md` (and optional `.json`); parse frontmatter or filename for `source`, `category`, `payer`, `tags`.
- **Optional URL ingest**: For each URL in a small list (e.g. `sources.txt`), run Trafilatura, then same chunk + embed + store.
- **Chunking**: Split by `chunk_size` (e.g. 500) with overlap (e.g. 50); keep metadata on each chunk.
- **Embed**: Use `sentence_transformers` model `all-MiniLM-L6-v2`.
- **Store**: Chroma collection with `metadata` (source, category, payer, denial_category, cpt, etc.).

### Step 3: Retrieval

- **Inputs**: `denial_code`, `denial_reason`, `payer`, `cpt_code`, `icd_code` (from claim).
- **Query construction**: Combine into one search string (e.g. “CO97 medical necessity Aetna CPT 99213”) or do multiple queries (by payer, by denial category) and merge.
- **Output**: Top-k chunks (e.g. 5–10) as a single context string to append to the prompt.

### Step 4: App integration

- After `get_denial_knowledge_base_context(denial_knowledge_base, ...)` (CSV lookup), call `retrieve_from_knowledge_base(claim_data)`.
- Concatenate: `denial_guidance_context + "\n\n" + rag_context`.
- Pass merged string into `build_prompt(..., denial_guidance_context=...)` (existing parameter).

### Step 5: CLI to build index

- `python -m knowledge_base.ingest` (or `scripts/build_knowledge_base.py`) to (re)build Chroma from curated (and optional URLs).
- Run after adding new curated files or new URLs.

---

## What We Don’t Do in MVP

- No heavy crawling of payer portals (many block scraping; start with curated text).
- No Firecrawl; Trafilatura only for optional, small URL list.
- No paid embedding API; sentence-transformers only.
- No deduplication or scheduled crawl yet (Phase 2).

---

## Optional: Trafilatura URL list (Phase 1.5)

When you’re ready to add a few public URLs (e.g. CMS):

1. Create `knowledge_base/sources.txt` or `knowledge_base/sources.json` with URLs.
2. In ingest, for each URL: `trafilatura.extract(request.get(url).text)` → markdown-like text → chunk → embed → Chroma.
3. Respect `robots.txt` and rate limits; use only public, allowed pages.

---

## One-Line Strategy

**Use curated markdown + optional Trafilatura to build a local policy knowledge base, embed with sentence-transformers, store in Chroma, and use RAG (retrieve + existing CSV) to generate smarter, policy-backed appeals—all with free tools.**
