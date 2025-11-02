## Quick start intent

Be productive fast: seed the demo DB, run the MCP servers, or import MCP modules directly.

-

## Big-picture architecture (what you'll work with)

- Data layer: `data/` contains seeds and generators. `data/init_db.py` seeds an embedded SQLite DB. `data/init_postgres.py` is a Postgres-oriented data generator (heavy; adjust counts before running).
- MCP layer: `mcp/*.py` modules expose domain-specific tools. Each `*_mcp.py` typically defines a Store class (DB access), Pydantic models, and a FastMCP instance (e.g. `client_mcp_server`).
- HTTP server: `mcp/mcp_server_http.py` mounts multiple FastMCP streamable HTTP apps at prefixes like `/client`, `/position`, `/quote`, `/market`, `/trades`, `/product` and manages lifecycle via MCP session managers.
- Agents: `sale_agent/` and `trader_agent/` show how Google ADK-based agents are wired to MCPs using `McpToolset` and `StreamableHTTPConnectionParams`. They read prompts from `config/prompt_templates.yaml` and LLM provider info from `config/config.py`.

## Project-specific conventions and patterns

- MCP modules return Pydantic models for structured responses and raw dicts for untyped/unstructured results to avoid Pydantic schema errors. See `mcp/clients_mcp.py` (ClientModel and ClientsResponse).
- Tool exposure: functions are decorated with `@<mcp_server>.tool()` (e.g. `@client_mcp_server.tool()`). Export the server and helper names in `__all__` so other modules can import them.
- DB path & config: centralised in `config/config.py`. Environment variables used:
  - `POSITIONS_DB` (overrides SQLite path), `LLM_PROVIDER`, `DEEPSEEK_API_KEY`, `AUDIT_LOG`.
- Agents expect MCP HTTP endpoints on `http://127.0.0.1:8003/<prefix>` by default (see `sale_agent/agent.py` and `trader_agent/agent.py`). Update URLs if you change server ports.

## Developer workflows and commands (concrete)

- Setup env (PowerShell):
  ```powershell
  python -m venv .venv
  ; .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Seed SQLite demo DB:
  ```powershell
  python data/init_db.py
  ```
- Run full FastMCP server (serves streamable HTTP endpoints):
  ```powershell
  python mcp\mcp_server_http.py
  # or
  uvicorn ascend_ai_adk.mcp.mcp_server_http:app --reload
  ```
- Test without FastMCP (importable functions):
  ```powershell
  python - <<'PY'
  from mcp.position_mcp import list_positions, get_position
  print(list_positions(limit=2).dict())
  PY
  ```

## Integration points & external dependencies

- FastMCP (optional): modules are written to work with or without the `fastmcp` runtime. If `fastmcp` is absent you can still import and call store functions directly.
- Google ADK: `sale_agent` and `trader_agent` use `google.adk.*` classes and the `McpToolset` adapter for tool calls.
- MCP Inspector (Node): `npx @modelcontextprotocol/inspector` — useful to browse endpoints at `http://localhost:8000` (or `8003` for full server).
- Postgres data generation in `data/init_postgres.py` — uses `sqlalchemy` and `psycopg2`; the script defaults to large record counts (1M rows) and connects to a server at port `11000` by default. Tweak `num_*` params before running.

## How to add a new MCP (pattern)

1. Create `mcp/<domain>_mcp.py`.
2. Implement a Store class that encapsulates DB access (follow `ClientStore` in `mcp/clients_mcp.py`).
3. Define Pydantic models for structured responses and response containers (count + list pattern).
4. Create a FastMCP instance: `mcp = FastMCP("Name", stateless_http=True)` and add `@mcp.tool()` decorated functions.
5. Export helpful names in `__all__` and, if mounting in the HTTP server, reference the module in `mcp/mcp_server_http.py` and set `.settings.streamable_http_path = '/'` if you want it mounted at root of its prefix.

## Pitfalls discovered in-code (do not invent fixes)

- Pydantic schema generation can fail for arbitrary objects — prefer returning dicts for unstructured results (project already follows this pattern).
- `data/init_postgres.py` will try to generate very large datasets and assumes a running Postgres service at a specific port — it's intended as a generator template, not a quick demo run.

## Files to inspect for examples

- `mcp/clients_mcp.py` — canonical MCP module (store, models, tools, exports)
- `mcp/mcp_server_http.py` — mounts servers and demonstrates lifecycle/session management
- `sale_agent/agent.py` & `trader_agent/agent.py` — how agents create McpToolset connections and read prompts from `config/prompt_templates.yaml`
- `config/config.py` & `config/prompt_templates.yaml` — centralised config and templates used by agents
- `data/init_db.py` — lightweight SQLite seeder used by the README quick-start

If anything above is unclear or there's a specific area you'd like the instructions to expand (examples, more commands, or add CI/test guidance), tell me which sections and I'll iterate.
