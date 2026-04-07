# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A personal health data aggregation project with four main components:

1. **My Health Record Downloader** (root) — Playwright-based bulk PDF downloader for Australia's My Health Record portal (`myrecord.ehealth.gov.au`). Requires headed browser for myGov MFA login.
2. **Medical Results DB** (root) — SQLite pipeline that extracts structured test results from downloaded pathology PDFs (`build_test_db.py`) and queries them (`query_results.py`). Database lives at `personal/medical_results.db`.
3. **Garmin MCP Server** (`garmin_mcp/`) — A separate sub-project (its own `pyproject.toml`, `.venv`, git history). MCP server exposing 96+ Garmin Connect tools. Includes `sync_garmin.py` for incremental sync to `garmin_export.db`, `import_garmin_export.py` for bulk JSON import, `browser_auth.py` for Playwright-based Garmin SSO workaround, and a Withings MCP sub-server at `garmin_mcp/withings-mcp-server/`.
4. **WHOOP MCP Server** (`whoop_mcp/`) — A separate sub-project. MCP server exposing WHOOP recovery, sleep, strain, and workout data via the official WHOOP Developer API (OAuth2). Includes `sync_whoop.py` for incremental sync to `whoop_export.db`. Tokens stored at `~/.whoop/tokens.json`.

## Commands

```bash
# Root project setup
uv sync
uv run playwright install chromium

# Run the My Health Record downloader (opens browser for myGov login)
uv run python my_health_record_downloader.py
uv run python my_health_record_downloader.py --output-dir ~/Documents/medical

# Build the medical results database from PDFs in personal/
uv run python build_test_db.py

# Query medical results
uv run python query_results.py panels
uv run python query_results.py tests
uv run python query_results.py trend <test-name>

# Run tests (root project)
uv run pytest tests/ -v
uv run pytest tests/test_downloader.py::TestBuildFilename -v   # single test class
uv run pytest tests/test_downloader.py::TestBuildFilename::test_basic_title -v  # single test

# Garmin MCP server (separate venv)
cd garmin_mcp && uv sync
cd garmin_mcp && uv run garmin-mcp          # start MCP server
cd garmin_mcp && uv run python sync_garmin.py  # sync Garmin data
cd garmin_mcp && uv run python browser_auth.py # Garmin SSO auth workaround
cd garmin_mcp && uv run pytest              # garmin tests

# WHOOP MCP server (separate venv)
cd whoop_mcp && uv sync
cd whoop_mcp && uv run whoop-auth           # OAuth2 login (opens browser)
cd whoop_mcp && uv run whoop-mcp            # start MCP server
cd whoop_mcp && uv run python sync_whoop.py # sync WHOOP data to SQLite
cd whoop_mcp && uv run pytest               # whoop tests
```

## Architecture Notes

- **Three independent Python projects**: Root uses `pyproject.toml` with playwright + click. `garmin_mcp/` and `whoop_mcp/` are separate projects with their own `pyproject.toml`, `uv.lock`, and `.venv`. They don't share dependencies.
- **`personal/` is gitignored**: Contains actual medical records, PDFs, and the `medical_results.db`. Never commit this directory.
- **Tests use a local HTTP server**: The downloader tests spin up a `FakePortalHandler` that simulates the My Health Record portal structure. Tests run headless Playwright against it — no real portal access needed.
- **Garmin auth flow**: Garmin's SSO endpoint is Cloudflare-blocked for programmatic access. `browser_auth.py` opens a real browser, captures the SSO ticket, and exchanges it for OAuth tokens stored at `~/.garminconnect`.
- **WHOOP auth flow**: Standard OAuth2 Authorization Code Grant. `whoop-auth` CLI opens a browser, user logs in at WHOOP, local callback server catches the redirect, exchanges for tokens stored at `~/.whoop/tokens.json`. Access tokens expire hourly; the client auto-refreshes using the refresh token.
- **MCP integration**: `.mcp.json` at root configures both Garmin and WHOOP MCP servers for Claude Desktop. Each sub-project also has its own `.mcp.json`.
