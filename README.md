# My Health Record PDF Downloader

Bulk download PDF medical records from the Australian [My Health Record](https://myrecord.ehealth.gov.au) portal using Playwright browser automation.

## How It Works

1. Opens a Chromium browser for you to log in via myGov (MFA required)
2. Expands the full document timeline by clicking "View more"
3. Visits each document, finds the PDF download link, and saves it
4. Skips documents without PDF attachments (e.g. eHealth Prescriptions)
5. Handles the idle timeout "Stay Logged In" dialog automatically

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
git clone https://github.com/realmindsai/my-health-record-downloader.git
cd my-health-record-downloader
uv sync
uv run playwright install chromium
```

## Usage

```bash
# Interactive mode (opens browser for myGov login)
uv run python my_health_record_downloader.py

# Custom output directory
uv run python my_health_record_downloader.py --output-dir ~/Documents/medical

# Headless mode (for testing only - no login possible)
uv run python my_health_record_downloader.py --headless
```

PDFs are saved to `~/Downloads/medical_records/` by default, named as `{Title}__{NN}.pdf`.

## Testing

```bash
uv run pytest tests/ -v
```

Tests use a local HTTP server that simulates the portal's page structure and PDF serving.

## Why Playwright?

We tried 10+ approaches before landing on Playwright:

| Approach | Why It Failed |
|----------|---------------|
| Chrome DevTools `fetch()` | CORS / mixed content blocking |
| `URL.createObjectURL` + `a.click()` | Chrome silently blocks after 1-2 downloads |
| Chrome download via CDP | Session cookies not transferred |
| Self-signed HTTPS relay | Chrome rejects self-signed certs in `fetch()` |
| HTTP relay server | Mixed content: HTTPS page cannot fetch HTTP |
| Puppeteer / Selenium | Same session cookie issues |
| **Playwright `page.request.get()`** | Carries session cookies, saves directly to disk |

## Portal Constraints

- **Multi-tab detection**: server-side + `window.name` check; only one tab allowed
- **Full page navigation**: not a SPA; DOM rebuilds on each navigation
- **~5 min idle timeout**: "Stay Logged In" dialog appears
- **Client-side PDF rendering**: PDF link appears via jQuery after page load

## License

MIT
