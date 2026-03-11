# My Health Record Download Workflow

Step-by-step guide for downloading all PDF medical records from the
Australian My Health Record portal using Claude-in-Chrome MCP.

See `../claude-skill/CLAUDE.md` for the full technical reference including
all portal constraints, troubleshooting, and failed approaches.

## Quick Reference

### Phase 1: Setup

```bash
# Generate trusted certificates (one-time)
brew install mkcert
mkcert -install
cd /tmp && mkcert localhost 127.0.0.1 ::1

# Create output directory and start relay
mkdir -p ~/Downloads/medical_records
python3 scripts/receiver_ssl.py &
```

### Phase 2: Browser Prep

1. Log into My Health Record via myGov in Chrome
2. Move the portal tab into the Claude-in-Chrome MCP tab group
3. Get the tab ID via `mcp__claude-in-chrome__tabs_context_mcp`

### Phase 3: Initialize

```javascript
// Inject via mcp__claude-in-chrome__javascript_tool
sessionStorage.setItem('dlIdx', '0');
sessionStorage.setItem('dlFailed', '');
```

### Phase 4: Download Loop

Repeat these two scripts for each document:

**Step 1 - Click next document (inject on home page, wait 20s):**
```javascript
async function step() {
  const p = window.location.pathname;
  if (!p.includes('home')) return 'NOT HOME: ' + p;
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

**Step 2 - Download PDF and go back (inject on doc page, wait 12s):**
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
      sessionStorage.setItem('dlIdx', String(idx + 1));
      const sb = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.toLowerCase().includes('stay logged'));
      if (sb) sb.click();
      setTimeout(() => { window.location.href = '/content/ncp/home.html'; }, 1500);
    })
    .catch(e => {
      sessionStorage.setItem('dlIdx', String(idx + 1));
      sessionStorage.setItem('dlFailed',
        (sessionStorage.getItem('dlFailed') || '') + idx + ',');
      setTimeout(() => { window.location.href = '/content/ncp/home.html'; }, 500);
    });
  'DL ' + fn;
} else if (p.includes('document') && !pdfLink) {
  sessionStorage.setItem('dlIdx', String(idx + 1));
  sessionStorage.setItem('dlFailed',
    (sessionStorage.getItem('dlFailed') || '') + idx + ',');
  setTimeout(() => { window.location.href = '/content/ncp/home.html'; }, 500);
  'SKIP ' + idx;
} else {
  'PAGE: ' + p;
}
```

**Check progress (inject anywhere):**
```javascript
'idx=' + sessionStorage.getItem('dlIdx')
  + ' failed=' + sessionStorage.getItem('dlFailed')
  + ' path=' + window.location.pathname;
```

### Phase 5: Verify

```bash
ls ~/Downloads/medical_records/*.pdf | wc -l
file ~/Downloads/medical_records/*.pdf | grep -v "PDF document"
find ~/Downloads/medical_records -name "*.pdf" -empty
kill $(lsof -ti:9877)
```
