# Model Context Protocol (MCP) — Appeal Drafter AI

This project exposes an **MCP server** so Cursor, Claude Desktop, or other MCP clients can call the same appeal pipeline as the Streamlit app (CSV guidance, optional Chroma RAG, LLM draft, payor form fill).

## Security (PHI)

Tools accept **patient and claim fields**. Treat the MCP client and host machine as within your **HIPAA / organizational trust boundary**. Do not expose this process on a shared or untrusted network without additional controls.

## Install

```bash
pip install -r requirements.txt
```

Ensure `.env` is configured (same as Streamlit): `LLM_PROVIDER`, `GEMINI_API_KEY` or `OPENAI_API_KEY`, etc.

## Run (manual / debugging)

From the `appeal_ai` project root:

```bash
python -m mcp_server
```

The server uses **stdio** for MCP. **Application logs** go to **stderr** and `logs/appeal_drafter.log` so **stdout** stays reserved for MCP JSON-RPC.

## Cursor

1. Open **Cursor Settings → MCP** (or edit the MCP config file your Cursor version uses).
2. Add a server entry that runs this project’s interpreter and module, for example:

```json
{
  "mcpServers": {
    "appeal-drafter": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\Users\RajaramanGopi\Downloads\Appeal Drafter AI\Project\appeal_ai"
    }
  }
}
```

Use the **full path** to `python` if Cursor does not see your venv (e.g. `C:\\path\\to\\.venv\\Scripts\\python.exe` on Windows).

3. Restart Cursor or reload MCP. You should see tools such as `draft_appeal_letter`, `get_denial_and_policy_guidance`, `list_payor_form_templates`, and `rag_index_status`.

## Exposed capabilities

| Name | Purpose |
|------|--------|
| `draft_appeal_letter` | Full pipeline including LLM; returns appeal text and optional filled payor template. |
| `get_denial_and_policy_guidance` | CSV + RAG text only (no LLM). |
| `list_payor_form_templates` | Payor folders with standard `.txt` forms. |
| `rag_index_status` | Whether `chroma_db` is ready. |
| Resource `appeal-drafter://payor-form-templates` | JSON list of template payors. |
| Prompt `appeal_letter_workflow` | Suggested multi-step workflow for the assistant. |

## Optional HTTP transport

The underlying SDK supports SSE / streamable HTTP; this repo’s entrypoint uses **stdio** only. For HTTP, adapt `run_mcp_server()` using the [MCP Python SDK](https://modelcontextprotocol.github.io/python-sdk/) deployment docs.
