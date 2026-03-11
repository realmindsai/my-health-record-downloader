---
name: my-health-record-downloader
description: Download all PDF medical records from the Australian My Health Record portal (myrecord.ehealth.gov.au) using Chrome browser automation with Claude-in-Chrome MCP. USE WHEN user says "download health records", "my health record", "download medical records", "health record PDFs", or wants to bulk-download documents from the Australian government health portal.
---

# My Health Record Bulk PDF Downloader

## When to Activate This Skill
- "Download my health records"
- "Get all my medical records from My Health Record"
- "Bulk download health record PDFs"
- User has My Health Record portal open in Chrome and wants documents saved locally

## Prerequisites
- Chrome browser with Claude-in-Chrome MCP extension installed
- User logged into My Health Record portal via myGov
- `mkcert` installed (`brew install mkcert`) with local CA set up (`mkcert -install`)
- Python 3 available for the relay server

## Why This Skill Exists
The My Health Record portal has no bulk download feature. Each document must be opened individually, and the PDF link must be clicked one at a time. This skill automates that process, but the portal has aggressive anti-automation measures that required significant reverse-engineering to work around.

## High-Level Workflow

```
1. User logs into My Health Record via myGov in Chrome
2. Tab must be in Claude-in-Chrome MCP tab group
3. Start mkcert-trusted HTTPS relay server on localhost:9877
4. For each document (loop driven by Claude Code):
   a. On home page: expand "View more", click document link
   b. On document page: fetch PDF via JS, POST to localhost relay
   c. Relay server saves PDF to disk
   d. Navigate back to home, repeat
5. Clean up relay server
```

## Quick Start

1. Read the full technical guide: `read ~/.claude/skills/my-health-record-downloader/CLAUDE.md`
2. Start the relay server: `python3 ~/.claude/skills/my-health-record-downloader/scripts/receiver_ssl.py`
3. Use the JavaScript snippets from CLAUDE.md to drive the download loop

## Key Technical Constraints

| Constraint | Impact | Solution |
|---|---|---|
| No multi-tab/window support | Portal detects and blocks multiple tabs via server-side session + `window.name` | Single tab only, never use iframes or `window.open` |
| Full page navigation (not SPA) | All injected JS is wiped on every page change | Drive the loop from Claude Code side, use `sessionStorage` for state |
| Chrome blocks programmatic blob downloads | `URL.createObjectURL` + `a.click()` gets silently blocked after first few files | Use mkcert HTTPS relay server on localhost |
| Mixed content blocking | HTTPS portal cannot fetch from HTTP localhost | Use mkcert for locally-trusted TLS certificates |
| ~5 min idle timeout | Session expires if idle too long | Click "Stay Logged In" button when present |
| jQuery click handlers on doc links | Standard `element.click()` works, but links use AJAX POST internally | Let the portal's jQuery handler do its thing |

## Supplementary Resources
- Full technical guide: `~/.claude/skills/my-health-record-downloader/CLAUDE.md`
- Relay server script: `~/.claude/skills/my-health-record-downloader/scripts/receiver_ssl.py`
