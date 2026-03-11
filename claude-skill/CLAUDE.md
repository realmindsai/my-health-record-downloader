# My Health Record Bulk PDF Downloader - Technical Guide

## Overview

This skill automates bulk downloading of PDF medical records from the Australian
My Health Record portal (https://myrecord.ehealth.gov.au). The portal has no
bulk download feature and employs aggressive anti-automation measures. This guide
documents every obstacle encountered and the solutions that work.

## Architecture

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Claude Code     │     │  Chrome Browser      │     │  HTTPS Relay     │
│  (orchestrator)  │────>│  (Claude-in-Chrome)  │────>│  Server          │
│                  │     │                      │     │  (localhost:9877) │
│  Drives loop:    │     │  Executes JS:        │     │                  │
│  - inject step   │     │  - click doc links   │     │  Receives POSTed │
│  - wait          │     │  - fetch PDF blobs   │     │  PDF blobs and   │
│  - inject dl     │     │  - POST to relay     │     │  saves to disk   │
│  - wait          │     │  - navigate back     │     │                  │
│  - repeat        │     │                      │     │                  │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
```

## Prerequisites

### 1. Chrome with Claude-in-Chrome MCP Extension
The user must have the Claude-in-Chrome extension installed and working.
The portal tab MUST be inside the MCP tab group (labeled "claude" in the tab bar).

### 2. mkcert for Trusted Local Certificates
```bash
brew install mkcert
mkcert -install              # One-time: installs local CA into system trust store
cd /tmp && mkcert localhost 127.0.0.1 ::1   # Generates cert files
```
This creates `/tmp/localhost+2.pem` and `/tmp/localhost+2-key.pem`.

**Why mkcert?** The portal runs on HTTPS. Browsers enforce mixed content blocking,
preventing HTTPS pages from making requests to HTTP servers. A self-signed cert
gets rejected by Chrome's fetch API. mkcert creates certs signed by a locally-trusted
CA that Chrome actually accepts, allowing the browser-to-localhost relay to work.

### 3. Python 3
For the relay server. No additional packages needed (uses stdlib only).

### 4. User Authentication
The user must manually log in via myGov. This involves multi-factor auth that
cannot be automated. Once logged in, the session persists in the browser tab.

---

## Portal Behavior and Constraints (Lessons Learned the Hard Way)

### Multi-Tab/Window Detection
The portal uses server-side session tracking AND `window.name` to detect multiple
tabs/windows. If detected, it locks the session into a persistent error state that
requires a full sign-out (`/signoff.html`) and re-login via myGov.

**What triggers it:**
- Opening any second tab/window to the same domain
- Using iframes that load portal pages
- Setting `window.name` to any value (the portal checks this)
- Using `history.back()` (confuses the portal's navigation tracking)

**What does NOT trigger it:**
- Using `sessionStorage` for state persistence
- Navigating via `window.location.href = '/content/ncp/home.html'`
- Making `fetch()` requests to the same origin

### Full Page Navigation (Not SPA)
The portal uses traditional full page navigation, NOT a single-page application.
Every link click reloads the entire page. This means:
- All injected JavaScript is wiped on every navigation
- MutationObservers, intervals, event listeners - all gone
- The download loop MUST be driven from the Claude Code side, not from in-page JS
- `sessionStorage` survives same-origin navigations (use this for state tracking)

### Document Link Click Mechanism
Document links on the home page use the selector `a.timeline__link.js-hro-document`.
They have jQuery-bound click handlers that:
1. POST to `/ncp/retrivedoclistdata` with params `docIds` and `retDocType`
2. Navigate to `/portal/documents/document`

Standard `element.click()` works because it triggers the jQuery handler.
Do NOT try to replicate the POST manually - just click the link element.

### PDF Links on Document Pages
The PDF link is rendered by client-side JavaScript, not present in the raw HTML.
It matches the selector `a[href*="getPDFContent"]` and points to a URL like:
`/ncp/getPDFContent?AttachmentID=CONTENT.PDF&AttachmentMimeType=application/pdf`

Not all document types have PDF attachments. Known types without PDFs:
- Discharge Summaries (sometimes)
- eHealth Prescriptions
- Documents with "System Error" on load

### Session Timeout
The portal has a ~5 minute idle timeout. A "Stay Logged In" dialog appears.
The download scripts should dismiss it when detected:
```javascript
const sb = Array.from(document.querySelectorAll('button'))
  .find(b => b.textContent.toLowerCase().includes('stay logged'));
if (sb) sb.click();
```

### Safe Navigation Pattern
To return to the home page after downloading a document, use:
```javascript
window.location.href = '/content/ncp/home.html';
```
Do NOT use:
- `history.back()` - triggers multi-tab detection
- `window.location.href = '/portal/home'` - may redirect to landing page
- `window.location.reload()` - redirects to `/portal/landing`

### "View More" Button
The home page timeline only shows recent documents. Older documents are loaded
by clicking "View more" buttons. These need to be clicked repeatedly until all
documents are visible (button disappears or becomes hidden).

---

## The Download Pipeline

### Why Browser Blob Downloads Fail

Chrome silently blocks programmatic downloads triggered by:
```javascript
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = 'filename.pdf';
a.click();  // Chrome blocks this after the first 1-2 files
```

Chrome's "multiple download" protection treats programmatic `<a>` clicks with
blob URLs as suspicious. It may download the first file but silently drop the rest.
There is no error, no prompt - the downloads simply don't happen.

Setting the `download` attribute on the existing PDF link and clicking it also
does not reliably trigger downloads.

### The mkcert HTTPS Relay Solution

Instead of triggering browser downloads, we fetch the PDF as a blob in JavaScript,
then POST it to a locally-trusted HTTPS server that saves it to disk.

```
Browser JS                    Localhost Server
─────────                    ────────────────
fetch(pdfLink.href)
  → blob
fetch('https://localhost:9877/', {
  method: 'POST',
  headers: {'X-Filename': 'report.pdf'},
  body: blob
})                      ──>   Receive POST body
                              Save to disk as report.pdf
                        <──   Return {saved, size}
```

This bypasses Chrome's download restrictions entirely because we're making a
standard HTTPS fetch request, not triggering a download.

---

## Step-by-Step Execution

### Phase 1: Setup

#### 1a. Generate mkcert certificates (if not already done)
```bash
mkcert -install  # one-time, installs local CA
cd /tmp && mkcert localhost 127.0.0.1 ::1
```

#### 1b. Create output directory
```bash
mkdir -p ~/Downloads/medical_records
```

#### 1c. Start the relay server
```bash
python3 ~/.claude/skills/my-health-record-downloader/scripts/receiver_ssl.py &
```
Verify it's working:
```bash
curl -s -X POST -H "X-Filename: test.txt" -d "ok" https://localhost:9877/
# Should return: {"saved": "test.txt", "size": 2}
rm ~/Downloads/medical_records/test.txt
```

#### 1d. Get browser tab context
Use `mcp__claude-in-chrome__tabs_context_mcp` to find the My Health Record tab.
The tab must be in the MCP tab group. Note the `tabId`.

### Phase 2: Initialize Session State

Using `mcp__claude-in-chrome__javascript_tool` on the portal tab:
```javascript
sessionStorage.setItem('dlIdx', '0');
sessionStorage.setItem('dlFailed', '');
```

Verify the page state:
```javascript
JSON.stringify({
  path: window.location.pathname,
  hasTimeline: !!document.querySelector('a.timeline__link'),
  linkCount: document.querySelectorAll('a.timeline__link').length,
  hasViewMore: !!Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.includes('View more'))
})
```

### Phase 3: Download Loop

Each document requires two script injections with waits between them.

#### Step Script (inject on home page, wait ~20s for doc page to load)
```javascript
async function step() {
  const p = window.location.pathname;
  if (!p.includes('home')) return 'NOT HOME: ' + p;

  // Expand all "View more" sections
  let c = 0;
  while (c < 10) {
    const b = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('View more'));
    if (!b || b.style.display === 'none') break;
    b.click();
    await new Promise(r => setTimeout(r, 2000));
    c++;
  }

  const links = document.querySelectorAll('a.timeline__link');
  const i = parseInt(sessionStorage.getItem('dlIdx') || '0');
  if (i >= links.length) return 'DONE all=' + links.length;

  sessionStorage.setItem('dlTitle', links[i].textContent.trim());
  await new Promise(r => setTimeout(r, 1000));
  links[i].click();
  return 'CLICK ' + i + '/' + links.length;
}
step().then(r => { window._r = r; });
```

#### Download Script (inject on document page, wait ~12s for relay + nav home)
```javascript
const p = window.location.pathname;
const pdfLink = document.querySelector('a[href*="getPDFContent"]');
const idx = parseInt(sessionStorage.getItem('dlIdx') || '0');
const t = sessionStorage.getItem('dlTitle') || 'doc';

if (p.includes('document') && pdfLink) {
  const fn = t.replace(/[^a-zA-Z0-9\-_ ]/g, '').replace(/\s+/g, '_')
    + '__' + String(idx + 1).padStart(2, '0') + '.pdf';

  fetch(pdfLink.href, { credentials: 'same-origin' })
    .then(r => r.blob())
    .then(blob => {
      if (blob.size === 0) throw new Error('Empty');
      return fetch('https://localhost:9877/', {
        method: 'POST',
        headers: { 'X-Filename': fn },
        body: blob
      });
    })
    .then(r => r.json())
    .then(j => {
      window._pdfRelay = 'SAVED:' + fn + ':' + j.size;
      sessionStorage.setItem('dlIdx', String(idx + 1));
      // Dismiss idle timeout dialog if present
      const sb = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.toLowerCase().includes('stay logged'));
      if (sb) sb.click();
      setTimeout(() => {
        window.location.href = '/content/ncp/home.html';
      }, 1500);
    })
    .catch(e => {
      window._pdfRelay = 'ERR:' + e.message;
      sessionStorage.setItem('dlIdx', String(idx + 1));
      sessionStorage.setItem('dlFailed',
        (sessionStorage.getItem('dlFailed') || '') + idx + ',');
      setTimeout(() => {
        window.location.href = '/content/ncp/home.html';
      }, 500);
    });

  'DL ' + fn;

} else if (p.includes('document') && !pdfLink) {
  // No PDF link - skip this document
  sessionStorage.setItem('dlIdx', String(idx + 1));
  sessionStorage.setItem('dlFailed',
    (sessionStorage.getItem('dlFailed') || '') + idx + ',');
  setTimeout(() => {
    window.location.href = '/content/ncp/home.html';
  }, 500);
  'SKIP ' + idx;

} else if (p.includes('error')) {
  'ERROR page';
} else {
  'WRONG PAGE: ' + p;
}
```

#### Status Check Script (inject anywhere to check progress)
```javascript
'idx=' + sessionStorage.getItem('dlIdx')
  + ' failed=' + sessionStorage.getItem('dlFailed')
  + ' path=' + window.location.pathname;
```

### Phase 4: Loop Orchestration

The loop is driven from Claude Code. For each document:

1. **Check** we're on home page (`path=/portal/home`)
2. **Inject** step script (expand + click)
3. **Wait** 20 seconds for document page to load
4. **Inject** download script (fetch + relay + navigate back)
5. **Wait** 12 seconds for relay + navigation home
6. **Check** status (idx incremented, path is home)
7. **Repeat** until `idx >= total document count`

If the step script click doesn't navigate (still on home after 20s), retry the
step script with a longer delay before the click.

### Phase 5: Verification and Cleanup

```bash
# Count downloaded PDFs
ls ~/Downloads/medical_records/*.pdf | wc -l

# Verify all are valid PDFs
file ~/Downloads/medical_records/*.pdf | grep -v "PDF document" || echo "All valid"

# Check for zero-byte files
find ~/Downloads/medical_records -name "*.pdf" -empty

# Kill the relay server
kill $(lsof -ti:9877) 2>/dev/null

# Clean up test files
rm -f ~/Downloads/medical_records/test.txt ~/Downloads/medical_records/healthcheck.txt
```

---

## Filename Convention

Files are named: `{DocumentTitle}__{SequenceNumber}.pdf`

Examples:
- `Pathology_Report_-_10th_March_2026__01.pdf`
- `Diagnostic_Imaging_Report_-_14th_November_2025__29.pdf`

The sequence number reflects the order on the portal timeline (most recent first).

---

## Troubleshooting

### "NOT HOME" after step script
The page navigated away from home unexpectedly. Check for session errors.
Navigate back: `window.location.href = '/content/ncp/home.html'`

### Multi-tab detection error
The session is corrupted. Must sign out and re-login:
1. Navigate to `/signoff.html`
2. User must log in again via myGov
3. Move the new tab into the MCP tab group
4. Resume from current `dlIdx`

### Empty blob (0 bytes)
The PDF link expired. This happens if you stay on a document page too long
before fetching. The fetch must happen promptly after navigation.

### Relay server dies
The Python server may exit if it encounters an error. Restart it:
```bash
python3 ~/.claude/skills/my-health-record-downloader/scripts/receiver_ssl.py &
```
Verify: `curl -s -X POST -H "X-Filename: test.txt" -d "ok" https://localhost:9877/`

### "Failed to fetch" on localhost POST
- Check relay server is running: `lsof -i:9877`
- Check mkcert certs exist: `ls /tmp/localhost+2*.pem`
- Regenerate if needed: `cd /tmp && mkcert localhost 127.0.0.1 ::1`
- Restart Chrome if mkcert CA was just installed (Chrome caches CA list)

### Session timeout
If the portal shows the idle timeout dialog, the script auto-dismisses it.
If the session actually expires, the page will redirect to the myGov login.
User must re-authenticate and resume from current `dlIdx`.

---

## What We Tried That Didn't Work

These approaches were all attempted and failed. Documenting them here to prevent
future time-wasting on dead ends.

### 1. In-Page Automation Loop (MutationObserver + setInterval)
**Idea:** Inject a self-contained script that runs the entire download loop.
**Why it failed:** Full page navigation destroys all injected JS state. Every
link click reloads the page, wiping the script.

### 2. Programmatic Blob Downloads (URL.createObjectURL + a.click)
**Idea:** Fetch PDF as blob, create object URL, trigger download via anchor click.
**Why it failed:** Chrome silently blocks programmatic downloads after the first
1-2 files. No error, no prompt - downloads just don't happen.

### 3. Setting download attribute on existing PDF link
**Idea:** Add `download="filename.pdf"` to the existing `<a>` tag and click it.
**Why it failed:** Chrome doesn't honor the download attribute for programmatic
clicks in the same way as user-initiated clicks.

### 4. iframe-based document loading
**Idea:** Load document pages in a hidden iframe to avoid full navigation.
**Why it failed:** Portal detects iframe as a second window, triggers multi-tab
error, locks the session.

### 5. history.back() for navigation
**Idea:** Use browser back button to return to home page after download.
**Why it failed:** Triggers multi-tab detection. The portal's navigation tracking
gets confused by back/forward navigation.

### 6. window.name for state persistence
**Idea:** Store download state in window.name (persists across navigations).
**Why it failed:** Portal uses window.name for its own multi-tab detection.
Setting it to any value triggers the multi-tab error.

### 7. HTTP localhost relay (no TLS)
**Idea:** POST blobs to http://localhost or http://127.0.0.1
**Why it failed:** Mixed content blocking. HTTPS pages cannot make fetch requests
to HTTP endpoints, even localhost. Chrome blocks it at the network level.

### 8. Self-signed HTTPS cert on localhost
**Idea:** Generate an OpenSSL self-signed cert for the relay server.
**Why it failed:** Chrome's fetch API rejects self-signed certificates.
Unlike browser navigation (which shows a warning), fetch requests fail silently.

### 9. Replicating the AJAX POST manually
**Idea:** Intercept jQuery.ajax, capture the POST parameters, replay them.
**Why it failed:** Overriding jQuery.ajax broke the click handler chain.
The correct field names are `docIds` and `retDocType` (not `recordDocId` and
`documentType`), but even with correct params, the handler chain was disrupted.

### 10. Fetching document page HTML directly
**Idea:** Use fetch() to get the document page HTML and parse out the PDF URL.
**Why it failed:** The PDF link is rendered by client-side JavaScript after page
load. The raw HTML doesn't contain it - it's injected by a script.
