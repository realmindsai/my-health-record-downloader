# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Playwright-based bulk PDF downloader for Australia's My Health Record portal (`myrecord.ehealth.gov.au`). Requires headed browser for myGov MFA login. Includes a SQLite pipeline for extracting structured test results from downloaded pathology PDFs.

## Commands

```bash
# Setup
uv sync
uv run playwright install chromium

# Run the downloader (opens browser for myGov login)
uv run python my_health_record_downloader.py
uv run python my_health_record_downloader.py --output-dir /path/to/incoming

# Organize downloaded records into date-sorted symlinks
uv run python organize_records.py

# Build the medical results database from PDFs
uv run python build_test_db.py

# Query medical results
uv run python query_results.py panels
uv run python query_results.py tests
uv run python query_results.py trend <test-name>

# Run tests
uv run pytest tests/ -v
uv run pytest tests/test_downloader.py::TestBuildFilename -v   # single test class
```

## Architecture Notes

- **`personal/` is gitignored**: Contains actual medical records, PDFs, and the `medical_results.db`. Never commit this directory.
- **`personal/incoming/`**: Raw downloads from the portal. Downloader targets this dir and skips files that already exist there.
- **`personal/organized/`**: Symlinks named `YYYY-MM-DD_ReportType_NN.pdf` pointing to `../incoming/`. Run `organize_records.py` after downloading to populate.
- **Tests use a local HTTP server**: The downloader tests spin up a `FakePortalHandler` that simulates the My Health Record portal structure. Tests run headless Playwright against it — no real portal access needed.
