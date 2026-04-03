# Updating the Knowledge Base with Current Online Data

## Short answer

- **The curated `.md` files do NOT automatically fetch from the internet.** They are static files in your repo. Nothing overwrites them from URLs.
- To get **current online data** into your system you have two options: **edit the .md files manually** (and re-run ingest), or **use URL fetch** so that content from URLs is pulled into the **vector index** when you run ingest (the .md files stay unchanged).

---

## How the two sources work

| Source | Auto-fetch? | Where it lives | How to update with “latest online” |
|--------|-------------|----------------|------------------------------------|
| **Curated `.md` files** (`knowledge_base/curated/`) | **No** | Files on disk; ingested into Chroma when you run ingest | Edit the .md files by hand (copy/paste from websites), then re-run `python -m knowledge_base.ingest` |
| **URLs in `sources.txt`** | **Only when you run ingest with `--urls`** | Fetched content goes **only into the Chroma index** (not into .md files) | Add URLs to `sources.txt`, then run `python -m knowledge_base.ingest --urls` (e.g. weekly) to refresh the index from those URLs |

So: **curated .md = static, hand-maintained**. **Online data = either manual copy into .md, or URL fetch into the index via `sources.txt` + `ingest --urls`.**

---

## Option 1: Update curated `.md` files manually (recommended for control)

Use this when you want the **source of truth** to be files you can edit and version (e.g. payor process, guidelines).

1. Open the relevant file, e.g.:
   - `knowledge_base/curated/payors/Aetna.md`
   - `knowledge_base/curated/guidelines/cms_coverage.md`
2. Go to the official website (e.g. Aetna provider portal, CMS), copy the current policy/process text.
3. Paste and adapt it into the .md file (keep headings, lists, key facts).
4. Save the file.
5. Rebuild the index so the app uses the new text:
   ```bash
   python -m knowledge_base.ingest
   ```
   (No `--urls` needed unless you also want to refresh URL-sourced content.)

**Pros:** Full control, versioned in git, no dependency on sites being crawlable.  
**Cons:** You must do it yourself and repeat when policies change.

---

## Option 2: Pull from URLs into the index (no .md changes)

Use this when you want **content from specific URLs** (e.g. a CMS NCD page) to be searchable in the app **without** editing .md files. The fetched content is **not** written back to any .md file; it only goes into Chroma.

1. **Add URLs** to `knowledge_base/sources.txt` (one URL per line; lines starting with `#` are ignored).  
   Example:
   ```
   https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=1
   https://www.cms.gov/medicare-coverage-database/details/ncd-details.aspx?NCDId=...
   ```
2. **Run ingest with URL fetch:**
   ```bash
   python -m knowledge_base.ingest --urls
   ```
   This will:
   - Load all curated .md (as before) and add them to Chroma.
   - For each URL in `sources.txt`, fetch the page, extract main content with **Trafilatura**, and add that content to Chroma as well.
   - Rebuild the **entire** Chroma index (curated + fetched). Existing .md files are **not** modified.

3. **To get “most current” data from those URLs later:** run the same command again (e.g. weekly):
   ```bash
   python -m knowledge_base.ingest --urls
   ```

**Pros:** No editing .md; you can refresh the index from the web on a schedule.  
**Cons:** Fetched content lives only in Chroma (not in .md); some sites block or limit scraping; you must re-run ingest to refresh.

---

## Summary: “What do I have to do to update with most current online data?”

- **If you maintain the curated .md files:**  
  Get the latest text from the web → paste into the right `.md` file → run `python -m knowledge_base.ingest`.

- **If you use URLs in `sources.txt`:**  
  Run `python -m knowledge_base.ingest --urls` whenever you want the index to reflect the current content of those URLs (e.g. weekly). The .md files are not updated automatically; only the vector index is.

- **You can do both:** Keep .md as your main, stable content and add a few URLs in `sources.txt` for specific pages you want refreshed when you run `ingest --urls`.
