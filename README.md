# My Health Record Bulk Downloader

Bulk download all PDF medical records from the Australian [My Health Record](https://myrecord.ehealth.gov.au) portal using Claude Code with Chrome browser automation.

## The Problem

My Health Record has no bulk export or download feature. Each document must be opened individually, and PDFs downloaded one at a time. For patients with dozens or hundreds of records, this is impractical.

## The Solution

This tool automates the entire process using:

- **Claude Code** as the orchestrator (drives the download loop)
- **Claude-in-Chrome MCP extension** for browser automation (clicks links, injects JavaScript)
- **mkcert HTTPS relay server** on localhost (receives PDFs from the browser and saves to disk)

### Why a relay server?

Chrome silently blocks programmatic blob downloads after the first few files. The portal runs on HTTPS, which blocks mixed-content requests to HTTP localhost. Self-signed certificates are rejected by Chrome's fetch API. The solution is `mkcert`, which creates locally-trusted TLS certificates that Chrome accepts, enabling a reliable browser-to-localhost file transfer pipeline.

## Architecture

```
Claude Code          Chrome Browser              HTTPS Relay Server
(orchestrator)  -->  (Claude-in-Chrome MCP)  -->  (localhost:9877)
                                                        |
Drives loop:         Executes JavaScript:          Saves PDFs to
- inject scripts     - clicks document links       ~/Downloads/
- wait for pages     - fetches PDF blobs             medical_records/
- check progress     - POSTs to localhost relay
- repeat             - navigates back to home
```

## Prerequisites

- **Claude Code** (Anthropic's CLI)
- **Claude-in-Chrome** MCP extension installed in Chrome
- **mkcert** (`brew install mkcert` on macOS)
- **Python 3** (for the relay server, stdlib only)
- **myGov account** with My Health Record linked

## Setup

### 1. Install mkcert and generate certificates

```bash
brew install mkcert
mkcert -install                              # One-time: install local CA
cd /tmp && mkcert localhost 127.0.0.1 ::1    # Generate cert files
```

### 2. Start the relay server

```bash
mkdir -p ~/Downloads/medical_records
python3 scripts/receiver_ssl.py &
```

Verify it works:
```bash
curl -s -X POST -H "X-Filename: test.txt" -d "ok" https://localhost:9877/
# Returns: {"saved": "test.txt", "size": 2}
```

### 3. Log into My Health Record

1. Open Chrome and log into My Health Record via [myGov](https://my.gov.au)
2. Navigate to your health record home page
3. Move the tab into the Claude-in-Chrome MCP tab group

### 4. Run the download

Use Claude Code and ask it to download your health records. If the skill is installed, Claude Code will follow the documented workflow automatically.

Alternatively, use the JavaScript snippets in `docs/workflow.md` to drive the process manually through the Claude-in-Chrome MCP tools.

## Portal Constraints (Hard-Won Knowledge)

The My Health Record portal has aggressive anti-automation measures:

| Constraint | What happens | Workaround |
|---|---|---|
| **Multi-tab detection** | Session locks permanently, requires re-login via myGov | Single tab only. Never use iframes, `window.open`, or `window.name` |
| **Full page navigation** | All injected JS is destroyed on every page change | Drive the loop from Claude Code, not from in-page scripts |
| **Chrome download blocking** | Blob URL downloads silently fail after 1-2 files | Use the mkcert HTTPS relay server instead |
| **Mixed content blocking** | HTTPS page cannot fetch from HTTP localhost | Use mkcert for locally-trusted TLS |
| **Session timeout (~5 min)** | "Stay Logged In" dialog appears | Auto-dismiss via JavaScript |
| **jQuery click handlers** | Document links use internal AJAX POST flow | Let the portal's jQuery handler fire naturally |
| **Client-side PDF rendering** | PDF link only appears after JavaScript execution | Must navigate to the page, not fetch HTML |

## What Didn't Work (So You Don't Have To Try)

We tried 10 different approaches before landing on the relay server solution:

1. **In-page automation loop** - JS wiped on every navigation
2. **Blob downloads** (`createObjectURL` + `a.click()`) - Chrome blocks after first few
3. **Download attribute on PDF link** - not honored for programmatic clicks
4. **iframe document loading** - triggers multi-tab detection
5. **`history.back()` navigation** - triggers multi-tab detection
6. **`window.name` for state** - triggers multi-tab detection
7. **HTTP localhost relay** - mixed content blocking
8. **Self-signed HTTPS cert** - Chrome fetch API rejects it
9. **Manual AJAX replay** - overriding jQuery.ajax breaks handler chain
10. **Fetching document HTML directly** - PDF link is client-side rendered

## File Structure

```
.
├── README.md
├── scripts/
│   └── receiver_ssl.py    # HTTPS relay server (Python 3, stdlib only)
├── docs/
│   └── workflow.md        # Detailed step-by-step workflow with JS snippets
└── claude-skill/
    ├── SKILL.md           # Claude Code skill (quick reference)
    └── CLAUDE.md          # Claude Code skill (full technical guide)
```

## Output

Files are saved to `~/Downloads/medical_records/` with names like:
- `Pathology_Report_-_10th_March_2026__01.pdf`
- `Diagnostic_Imaging_Report_-_14th_November_2025__29.pdf`

## License

MIT

## Contributing

Found a portal change that breaks the workflow? PRs welcome. The portal's behavior may change over time as the Australian Digital Health Agency updates it.

---

Built by [Real Minds AI](https://realmindsai.com.au) with Claude Code.
