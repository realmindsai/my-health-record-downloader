# ABOUTME: Tests for the My Health Record PDF downloader.
# ABOUTME: Uses a local test server to simulate the portal's page structure and PDF serving.

import http.server
import json
import threading
import time
from pathlib import Path

import pytest

from my_health_record_downloader import (
    build_filename,
    download_documents,
)


# --- Unit tests for filename generation ---


class TestBuildFilename:
    def test_basic_title(self):
        result = build_filename("Pathology Report - 10th March 2026", 0)
        assert result == "Pathology_Report_-_10th_March_2026__01.pdf"

    def test_special_characters_stripped(self):
        result = build_filename("Report (Lab) / Test #3", 5)
        assert result == "Report_Lab_Test_3__06.pdf"

    def test_whitespace_collapsed(self):
        result = build_filename("Pathology   Report  -   10th", 0)
        assert result == "Pathology_Report_-_10th__01.pdf"

    def test_index_padding(self):
        result = build_filename("Doc", 99)
        assert result == "Doc__100.pdf"

    def test_empty_title(self):
        result = build_filename("", 0)
        assert result == "document__01.pdf"


# --- Integration tests with a fake portal server ---

FAKE_HOME_HTML = """
<html><body>
<a class="timeline__link js-hro-document" href="/portal/documents/document?id=1">Pathology Report - 10th March 2026</a>
<a class="timeline__link js-hro-document" href="/portal/documents/document?id=2">Diagnostic Imaging Report - 5th Feb 2026</a>
<a class="timeline__link js-hro-document" href="/portal/documents/document?id=3">Discharge Summary - 1st Jan 2026</a>
</body></html>
"""

FAKE_DOC_WITH_PDF = """
<html><body>
<h1>Document View</h1>
<a href="/ncp/getPDFContent?AttachmentID=CONTENT.PDF&AttachmentMimeType=application/pdf">Download PDF</a>
</body></html>
"""

FAKE_DOC_NO_PDF = """
<html><body>
<h1>Document View</h1>
<p>No PDF attachment available for this document type.</p>
</body></html>
"""

FAKE_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing purposes only"


class FakePortalHandler(http.server.BaseHTTPRequestHandler):
    """Simulates the My Health Record portal pages."""

    def do_GET(self):
        if self.path == "/portal/home" or self.path == "/content/ncp/home.html":
            self._respond(200, "text/html", FAKE_HOME_HTML)
        elif self.path.startswith("/portal/documents/document"):
            doc_id = self.path.split("id=")[-1] if "id=" in self.path else "1"
            if doc_id == "3":
                self._respond(200, "text/html", FAKE_DOC_NO_PDF)
            else:
                self._respond(200, "text/html", FAKE_DOC_WITH_PDF)
        elif self.path.startswith("/ncp/getPDFContent"):
            self._respond(200, "application/pdf", FAKE_PDF_BYTES)
        else:
            self._respond(404, "text/plain", "Not found")

    def _respond(self, status, content_type, body):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress server logs during tests


@pytest.fixture(scope="module")
def fake_portal():
    """Start a fake portal HTTP server for integration tests."""
    server = http.server.HTTPServer(("127.0.0.1", 0), FakePortalHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary output directory."""
    d = tmp_path / "medical_records"
    d.mkdir()
    return d


class TestDownloadDocuments:
    def test_downloads_pdfs_and_skips_no_pdf(self, fake_portal, output_dir):
        """Downloads docs with PDF links, skips those without."""
        result = download_documents(
            home_url=f"{fake_portal}/portal/home",
            back_url=f"{fake_portal}/content/ncp/home.html",
            output_dir=output_dir,
            headless=True,
        )
        pdfs = list(output_dir.glob("*.pdf"))
        assert len(pdfs) == 2
        assert result["downloaded"] == 2
        assert result["skipped"] == 1
        assert 3 in result["skipped_indices"]

    def test_pdf_content_is_correct(self, fake_portal, output_dir):
        """Saved PDFs contain the correct content from the server."""
        download_documents(
            home_url=f"{fake_portal}/portal/home",
            back_url=f"{fake_portal}/content/ncp/home.html",
            output_dir=output_dir,
            headless=True,
        )
        pdfs = sorted(output_dir.glob("*.pdf"))
        assert pdfs[0].read_bytes() == FAKE_PDF_BYTES

    def test_filenames_match_convention(self, fake_portal, output_dir):
        """Files use the {Title}__{NN}.pdf naming convention."""
        download_documents(
            home_url=f"{fake_portal}/portal/home",
            back_url=f"{fake_portal}/content/ncp/home.html",
            output_dir=output_dir,
            headless=True,
        )
        names = sorted(f.name for f in output_dir.glob("*.pdf"))
        assert names[0] == "Diagnostic_Imaging_Report_-_5th_Feb_2026__02.pdf"
        assert names[1] == "Pathology_Report_-_10th_March_2026__01.pdf"

    def test_empty_output_dir_created(self, fake_portal, tmp_path):
        """Output directory is created if it doesn't exist."""
        new_dir = tmp_path / "new_records"
        download_documents(
            home_url=f"{fake_portal}/portal/home",
            back_url=f"{fake_portal}/content/ncp/home.html",
            output_dir=new_dir,
            headless=True,
        )
        assert new_dir.exists()
        assert len(list(new_dir.glob("*.pdf"))) == 2
