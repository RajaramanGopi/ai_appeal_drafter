# Appeal Drafter AI — E2E Flow & Run Guide

This document explains the **end-to-end flow** of the project, **how to run it**, and **what each folder and file does** from start to finish.

---

## 1. How to Run the Project

### Prerequisites

- **Python 3.10+**
- **pip** (to install dependencies)

### Step 1: Install dependencies

From the project root (`appeal_ai`):

```bash
cd appeal_ai
pip install -r requirements.txt
```

### Step 2: Configure environment

1. Copy the example env file:
   ```bash
   copy .env.example .env
   ```
   (On macOS/Linux: `cp .env.example .env`)

2. Edit **`.env`** and set:
   - **LLM provider**: `LLM_PROVIDER=gemini` or `LLM_PROVIDER=openai`
   - **API key** for that provider:
     - Gemini: `GEMINI_API_KEY=your_key` (from [Google AI Studio](https://aistudio.google.com/app/apikey))
     - OpenAI: `OPENAI_API_KEY=your_key`
   - Optional: `GEMINI_MODEL` or `OPENAI_MODEL` to change the model name.

   If `LLM_PROVIDER` is not set, the app auto-detects: Gemini if `GEMINI_API_KEY` is set, otherwise OpenAI.

### Step 3: (Optional) Build the knowledge base index

For **policy-backed appeals** (RAG), build the Chroma index once:

```bash
python -m knowledge_base.ingest
```

First run may take a few minutes (downloads the embedding model). After that, the app will use the index when generating appeals. You can skip this; the app still works with CSV-only guidance.

### Step 4: Start the app

```bash
streamlit run app.py
```

The terminal will show a URL (e.g. `http://localhost:8501`). Open it in a browser.

### Step 5: Use the app

1. Fill in the **sidebar** (Payer Name, Request type, Denial Code, CPT, ICD, Denial Reason, Patient, Date of Service, Provider).
2. Click **Generate Appeal Letter**.
3. Wait for the draft; then read it, download the letter, and if a payor form exists, edit and download the filled form.

---

## 2. E2E Flow (Start to End)

High-level: **User clicks “Generate Appeal Letter”** → **Claim data is collected** → **Guidance is gathered (CSV + optional RAG)** → **Prompt is built** → **LLM generates the appeal** → **Result is shown and payor form is filled (if any)**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTRY POINT: streamlit run app.py                                          │
│  → Streamlit loads app.py and renders the UI                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER: Fills sidebar and clicks "Generate Appeal Letter"                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  app.py: Build claim_data dict from sidebar inputs                           │
│  (payer, request_type, denial_code, cpt_code, icd_code, denial_reason,       │
│   patient_name, dos, provider)                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
┌───────────────────────────────────┐     ┌───────────────────────────────────┐
│  CSV DENIAL GUIDANCE              │     │  RAG (if chroma_db exists)       │
│  data_loader.load_denial_         │     │  retrieve.retrieve_context_       │
│  knowledge_base()                 │     │  for_claim(claim_data)             │
│  → data/denial_knowledge_base -   │     │  → Chroma vector search by         │
│    Main.csv                       │     │    payer, denial, CPT, reason     │
│  data_loader.get_denial_          │     │  → Top-k policy/guideline chunks   │
│  knowledge_base_context(          │     │  → Appended to denial_guidance_    │
│    denial_knowledge_base,         │     │    context                         │
│    denial_code, denial_reason)    │     │                                    │
│  → Matched rows → guidance text  │     │  (Uses knowledge_base/curated/     │
│  → denial_guidance_context        │     │   content indexed by ingest)      │
└───────────────────────────────────┘     └───────────────────────────────────┘
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  app.py: denial_guidance_context = CSV guidance + (optional) RAG excerpts   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  llm_client.generate_appeal(claim_data, denial_guidance_context)             │
│  → Reads LLM_PROVIDER from .env → calls _generate_openai or _generate_gemini  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  prompt_template.build_prompt(claim_data, denial_guidance_context)           │
│  → Builds full prompt: letter type, guidance block, claim details,            │
│    denial reason, and instructions (clinical justification, medical          │
│    necessity, documentation references)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLM API (OpenAI or Gemini)                                                 │
│  → System: "Expert US healthcare RCM appeal specialist"                    │
│  → User: full prompt                                                        │
│  → Returns appeal letter text                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  app.py: Display appeal, download button                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  form_loader.get_filled_form_for_payer(payer, claim_data, appeal,            │
│                                        request_type)                         │
│  → Looks under payor_standard_appeal_forms/<PayorName>/ for                   │
│    appeal_form.txt or reconsideration_form.txt                               │
│  → Replaces {{APPEAL_BODY}}, {{PATIENT_NAME}}, etc. with claim + appeal      │
│  → If found: show filled form and download button                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER: Reviews appeal + form, downloads as needed. E2E complete.             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Folder-Level Overview

| Folder | Purpose | When it’s used |
|--------|---------|----------------|
| **`appeal_ai/`** (project root) | Contains the app entry point, config, and all modules. | You run `streamlit run app.py` and `python -m knowledge_base.ingest` from here. |
| **`data/`** | Holds the **denial knowledge base CSV**. | Read at runtime by `utils/data_loader.py` for denial-code → guidance lookup. |
| **`utils/`** | **data_loader**: load CSV and get guidance by denial code. **form_loader**: find and fill payor forms. | Used on every “Generate Appeal Letter” click. |
| **`knowledge_base/`** | RAG: **curated** content, **ingest** (build Chroma index), **retrieve** (vector search). | Ingest: run once (or after adding content). Retrieve: called from app when index exists. |
| **`knowledge_base/curated/`** | Markdown (and optional JSON) for payors, guidelines, denial categories. | Read by `knowledge_base/ingest.py` when you run `python -m knowledge_base.ingest`. |
| **`payor_standard_appeal_forms/`** | One folder per payor (e.g. `Aetna/`) with `appeal_form.txt` and/or `reconsideration_form.txt`. | Form loader matches “Payer Name” to folder and fills placeholders with claim + appeal. |
| **`chroma_db/`** | Chroma vector DB persistence (created by ingest). | Used by `knowledge_base/retrieve.py` at runtime if the folder and collection exist. |
| **`logs/`** | Log file from `config.logging` (e.g. `appeal_drafter.log`). | Created when the app runs; useful for debugging. |
| **`docs/`** | Implementation plan and this E2E/run guide. | Reference only. |

---

## 4. File-Level Reference

### 4.1 Entry point and UI

| File | Role |
|------|------|
| **`app.py`** | **Entry point** for the Streamlit app. Loads `.env`, configures logging, renders sidebar (claim fields) and “Generate Appeal Letter” button. On click: builds `claim_data`, loads CSV guidance, optionally runs RAG retrieval, calls `generate_appeal()`, then gets filled payor form. Shows appeal text and download buttons. |

### 4.2 Configuration and logging

| File | Role |
|------|------|
| **`.env`** | Secrets and options: `LLM_PROVIDER`, `GEMINI_API_KEY` or `OPENAI_API_KEY`, optional model names. Not committed. |
| **`.env.example`** | Template for `.env`; safe to commit. |
| **`config/logging.py`** | Sets up logging (console + optional `logs/appeal_drafter.log`), format, and level. Called once from `app.py`. |

### 4.3 LLM and prompt

| File | Role |
|------|------|
| **`llm_client.py`** | **generate_appeal(claim_data, denial_guidance_context)**: selects OpenAI or Gemini from `.env`, calls **build_prompt()**, then the corresponding API. Returns the appeal text or raises **LLMError**. |
| **`prompt_template.py`** | **build_prompt(claim_data, denial_guidance_context)**: builds the user prompt (letter type, optional guidance block, claim details, denial reason, instructions). Returns one string for the LLM. |

### 4.4 Data and forms

| File | Role |
|------|------|
| **`data/denial_knowledge_base - Main.csv`** | Rows keyed by EOB/claim adjustment/remark codes; columns include category, appeal strategy, required documents, payer notes. Used for exact denial-code lookup. |
| **`utils/data_loader.py`** | **load_denial_knowledge_base()**: reads the Main CSV from `data/`. **get_denial_knowledge_base_context(denial_knowledge_base, denial_code, denial_reason)**: parses denial code (e.g. CO97, N362), finds matching rows, returns formatted guidance string. |
| **`utils/form_loader.py`** | **list_available_payors()**: lists folder names under `payor_standard_appeal_forms/` that contain a form file. **find_form_for_payer(payer_name, request_type)**: matches payer to folder, picks appeal_form.txt or reconsideration_form.txt. **fill_form()**: replaces {{PLACEHOLDER}} with claim + appeal. **get_filled_form_for_payer()**: find + fill in one call. |
| **`payor_standard_appeal_forms/<Payor>/appeal_form.txt`** | Template with placeholders (e.g. `{{APPEAL_BODY}}`, `{{PATIENT_NAME}}`). One such file (or reconsideration_form.txt) per payor. |

### 4.5 Knowledge base (RAG)

| File | Role |
|------|------|
| **`config/settings.py`** | All paths (data, forms, KB, Chroma), chunk/top_k, ingest allowlist, LLM timeout, log rotation, prompt limits. |
| **`knowledge_base/ingest.py`** | **run_ingest(use_urls=False)**: loads all curated `.md` (and optional `.json`) from payors, guidelines, denial_categories; optionally fetches URLs from `sources.txt` with Trafilatura; chunks text; embeds with sentence-transformers; writes to Chroma. Run via `python -m knowledge_base.ingest` (and `--urls` if using URLs). |
| **`knowledge_base/retrieve.py`** | **retrieve_context_for_claim(claim_data, top_k)**: builds query from payer, denial code, CPT, ICD, denial reason; loads Chroma collection; encodes query with same embedding model; returns top-k chunks as one formatted string. **is_knowledge_base_available()**: returns True if Chroma index exists and is usable. |
| **`knowledge_base/curated/payors/*.md`** | Per-payor appeal process (e.g. Aetna, UHC, Medicare). Ingested and searched by payer + denial/CPT/reason. |
| **`knowledge_base/curated/guidelines/*.md`** | CMS, CPT, medical necessity summaries. Ingested and retrieved for policy-backed appeals. |
| **`knowledge_base/curated/denial_categories/*.md`** | High-level denial categories and strategies. Ingested for semantic search. |
| **`knowledge_base/sources.txt`** | Optional list of URLs (one per line) for Trafilatura when running ingest with `--urls`. |

### 4.6 Other

| File | Role |
|------|------|
| **`requirements.txt`** | Python dependencies (Streamlit, pandas, OpenAI, Gemini, dotenv, sentence-transformers, chromadb, etc.). |
| **`README.md`** | Setup, run, data, and knowledge base instructions. |
| **`docs/KNOWLEDGE_BASE_IMPLEMENTATION_PLAN.md`** | Architecture and free-tools strategy for the knowledge base. |

---

## 5. What to Check at Each Stage

### Before first run

- [ ] **Python 3.10+** installed.
- [ ] **`.env`** created from `.env.example` and **LLM_PROVIDER** + **API key** set.
- [ ] **`pip install -r requirements.txt`** completed without errors.
- [ ] **`data/denial_knowledge_base - Main.csv`** present if you want CSV denial guidance (app runs without it but with no code-specific guidance).

### When running the app

- [ ] **`streamlit run app.py`** starts and a URL is shown.
- [ ] Sidebar shows “Claim Details” and “Standard forms available for: …” if any payor folders exist.
- [ ] After clicking “Generate Appeal Letter”: no red error in the UI; appeal text and download button appear.
- [ ] If you entered a payer that has a form (e.g. Aetna), a filled form section and download appear.
- [ ] If the LLM fails: check `.env` (correct provider and key); check **`logs/appeal_drafter.log`** for details.

### Optional: knowledge base (RAG)

- [ ] **`chroma_db/`** exists after running **`python -m knowledge_base.ingest`**.
- [ ] No errors during ingest; terminal shows “Ingested N chunks into Chroma”.
- [ ] When generating an appeal, **`logs/appeal_drafter.log`** shows “RAG context appended” if the index was used.

### Adding content later

- [ ] **New payor form**: add `payor_standard_appeal_forms/<PayorName>/appeal_form.txt` (and placeholders); restart or refresh the app.
- [ ] **New denial rows**: edit **`data/denial_knowledge_base - Main.csv`**; no restart needed (CSV is read on each request).
- [ ] **New RAG content**: add or edit `.md` under **`knowledge_base/curated/`**, then run **`python -m knowledge_base.ingest`** again.

---

## 6. One-Page Flow Summary

| Step | Where | What happens |
|------|--------|----------------|
| 1 | You | `streamlit run app.py` from `appeal_ai/` |
| 2 | `app.py` | Loads `.env`, logging; shows UI with sidebar + button |
| 3 | You | Fill claim fields, click “Generate Appeal Letter” |
| 4 | `app.py` | Builds `claim_data` dict |
| 5 | `utils/data_loader` | Loads CSV, gets guidance by denial code → `denial_guidance_context` |
| 6 | `knowledge_base/retrieve` | If Chroma exists, vector search by claim → append to `denial_guidance_context` |
| 7 | `llm_client` | Picks OpenAI or Gemini from `.env` |
| 8 | `prompt_template` | Builds full prompt from claim + guidance |
| 9 | LLM API | Returns appeal letter text |
| 10 | `app.py` | Shows appeal + download button |
| 11 | `utils/form_loader` | If payer matches a folder, fills form template with claim + appeal |
| 12 | `app.py` | Shows filled form + download (if any) |

End-to-end: **UI → claim_data → CSV + RAG → prompt → LLM → appeal → form fill → display and download.**
