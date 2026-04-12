# ABOUTME: Bulk downloads PDF medical records from the Australian My Health Record portal.
# ABOUTME: Uses Playwright for browser automation with headed mode for myGov MFA login.

import re
import time
from pathlib import Path

import click
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout


PORTAL_HOME = "https://myrecord.ehealth.gov.au/portal/home"
PORTAL_BACK = "https://myrecord.ehealth.gov.au/content/ncp/home.html"
TIMELINE_LINK_SELECTOR = "a.timeline__link"
VIEW_MORE_TEXT = "View more"
PDF_LINK_SELECTOR = "a[href*='getPDFContent']"
STAY_LOGGED_IN_TEXT = "stay logged"


def build_filename(title: str, index: int) -> str:
    """Build a PDF filename from a document title and sequence index.

    Strips special characters, collapses whitespace to underscores,
    and appends a zero-padded sequence number.
    """
    if not title.strip():
        title = "document"
    sanitized = re.sub(r"[^a-zA-Z0-9\-_ ]", "", title)
    sanitized = re.sub(r"\s+", "_", sanitized.strip())
    return f"{sanitized}__{index + 1:02d}.pdf"


def _expand_timeline(page: Page) -> None:
    """Click all 'View more' buttons to reveal the full document timeline."""
    for _ in range(20):
        buttons = page.query_selector_all("button")
        view_more = None
        for btn in buttons:
            text = btn.text_content() or ""
            if VIEW_MORE_TEXT in text and btn.is_visible():
                view_more = btn
                break
        if not view_more:
            break
        view_more.click()
        page.wait_for_timeout(2000)


def _dismiss_stay_logged_in(page: Page) -> None:
    """Dismiss the 'Stay Logged In' idle timeout dialog if present."""
    buttons = page.query_selector_all("button")
    for btn in buttons:
        text = (btn.text_content() or "").lower()
        if STAY_LOGGED_IN_TEXT in text:
            btn.click()
            break


_DEFAULT_OUTPUT_DIR = Path(__file__).parent / "personal" / "incoming"


def download_documents(
    home_url: str = PORTAL_HOME,
    back_url: str = PORTAL_BACK,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    headless: bool = False,
    wait_for_login: bool = False,
) -> dict:
    """Download all PDF documents from the My Health Record timeline.

    Args:
        home_url: URL of the portal home page with the document timeline.
        back_url: URL to navigate back to after each document download.
        output_dir: Directory to save downloaded PDFs.
        headless: Run browser in headless mode (for testing).
        wait_for_login: Pause for manual myGov login before starting.

    Returns:
        Dict with keys: downloaded, skipped, skipped_indices, filenames.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "downloaded": 0,
        "skipped": 0,
        "skipped_indices": [],
        "filenames": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        page.goto(home_url, wait_until="networkidle")

        if wait_for_login:
            input("\n>>> Log in via myGov in the browser, then press Enter here to continue...\n")
            page.goto(home_url, wait_until="networkidle")

        # Expand the full timeline
        _expand_timeline(page)

        # Collect all document links
        links = page.query_selector_all(TIMELINE_LINK_SELECTOR)
        total = len(links)
        click.echo(f"Found {total} documents on timeline.")

        for i in range(total):
            # Re-query links after each navigation (DOM is rebuilt)
            _expand_timeline(page)
            links = page.query_selector_all(TIMELINE_LINK_SELECTOR)

            if i >= len(links):
                click.echo(f"  [{i+1}/{total}] Link index out of range, stopping.")
                break

            title = (links[i].text_content() or "").strip()
            filename = build_filename(title, i)
            click.echo(f"  [{i+1}/{total}] {title}...")

            # Click the document link and wait for navigation
            links[i].click()
            try:
                page.wait_for_url("**/documents/document**", timeout=30000)
            except PlaywrightTimeout:
                click.echo(f"    SKIP - page did not navigate to document view")
                result["skipped"] += 1
                result["skipped_indices"].append(i + 1)
                page.goto(back_url, wait_until="networkidle")
                continue

            # Wait for the page to render the PDF link
            page.wait_for_timeout(2000)

            # Look for the PDF download link
            pdf_link = page.query_selector(PDF_LINK_SELECTOR)
            if not pdf_link:
                click.echo(f"    SKIP - no PDF attachment")
                result["skipped"] += 1
                result["skipped_indices"].append(i + 1)
                page.goto(back_url, wait_until="networkidle")
                continue

            # Fetch the PDF using the page's request context (carries session cookies)
            pdf_href = pdf_link.get_attribute("href")
            if pdf_href and not pdf_href.startswith("http"):
                # Relative URL — resolve against the page origin
                origin = page.evaluate("window.location.origin")
                pdf_href = origin + pdf_href

            response = page.request.get(pdf_href)

            if response.status != 200 or len(response.body()) == 0:
                click.echo(f"    SKIP - PDF fetch failed (status={response.status})")
                result["skipped"] += 1
                result["skipped_indices"].append(i + 1)
                page.goto(back_url, wait_until="networkidle")
                continue

            # Save to disk — skip if already downloaded
            filepath = output_dir / filename
            if filepath.exists():
                click.echo(f"    SKIP - already exists: {filename}")
                result["skipped"] += 1
                result["skipped_indices"].append(i + 1)
                page.goto(back_url, wait_until="networkidle")
                continue
            filepath.write_bytes(response.body())
            click.echo(f"    SAVED {filename} ({len(response.body())} bytes)")
            result["downloaded"] += 1
            result["filenames"].append(filename)

            # Dismiss idle timeout dialog if present
            _dismiss_stay_logged_in(page)

            # Navigate back to home
            page.goto(back_url, wait_until="networkidle")

        browser.close()

    return result


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(),
    default=str(_DEFAULT_OUTPUT_DIR),
    help="Directory to save downloaded PDFs.",
)
@click.option(
    "--headless",
    is_flag=True,
    default=False,
    help="Run browser in headless mode (skips login wait).",
)
def main(output_dir: str, headless: bool) -> None:
    """Download all PDF medical records from My Health Record."""
    click.echo("My Health Record Bulk PDF Downloader")
    click.echo("=" * 40)

    result = download_documents(
        output_dir=Path(output_dir),
        headless=headless,
        wait_for_login=not headless,
    )

    click.echo()
    click.echo(f"Done! {result['downloaded']} PDFs downloaded, {result['skipped']} skipped.")
    if result["skipped_indices"]:
        click.echo(f"Skipped document numbers: {result['skipped_indices']}")
    click.echo(f"Files saved to: {output_dir}")


if __name__ == "__main__":
    main()
