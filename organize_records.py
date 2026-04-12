# ABOUTME: Creates date-sorted symlinks in personal/organized/ pointing to personal/incoming/ files.
# ABOUTME: Parses My Health Record portal filenames and reorganizes them as YYYY-MM-DD_Type_NN.pdf.

import re
import sys
from pathlib import Path

import click

MONTH_MAP = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
}

# Matches: SomeReport_Type_-_DDth_Month_YYYY__NN.pdf
FILENAME_PATTERN = re.compile(
    r"^(?P<type>.+?)_-_(?P<day>\d+)(?:st|nd|rd|th)_(?P<month>[A-Z][a-z]+)_(?P<year>\d{4})__(?P<num>\d+)\.pdf$"
)


def parse_filename(filename: str) -> dict | None:
    """Parse a portal filename into structured components. Returns None if unrecognized."""
    m = FILENAME_PATTERN.match(filename)
    if not m:
        return None
    month_num = MONTH_MAP.get(m.group("month"))
    if not month_num:
        return None
    return {
        "type": m.group("type"),
        "date": f"{m.group('year')}-{month_num}-{int(m.group('day')):02d}",
        "num": int(m.group("num")),
    }


def organized_name(parsed: dict) -> str:
    """Build the sortable organized filename: YYYY-MM-DD_ReportType_NN.pdf"""
    return f"{parsed['date']}_{parsed['type']}_{parsed['num']:02d}.pdf"


@click.command()
@click.option(
    "--incoming",
    default=None,
    help="Path to incoming/ directory. Defaults to personal/incoming/ relative to this script.",
)
@click.option(
    "--organized",
    default=None,
    help="Path to organized/ directory. Defaults to personal/organized/ relative to this script.",
)
def main(incoming: str | None, organized: str | None) -> None:
    """Create date-sorted symlinks in organized/ for all PDFs in incoming/."""
    base = Path(__file__).parent / "personal"
    incoming_dir = Path(incoming) if incoming else base / "incoming"
    organized_dir = Path(organized) if organized else base / "organized"

    if not incoming_dir.exists():
        click.echo(f"ERROR: incoming/ not found at {incoming_dir}", err=True)
        sys.exit(1)

    organized_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    unrecognized = []

    for pdf in sorted(incoming_dir.glob("*.pdf")):
        parsed = parse_filename(pdf.name)
        if parsed is None:
            unrecognized.append(pdf.name)
            continue

        link_name = organized_name(parsed)
        link_path = organized_dir / link_name

        # Relative path from organized/ back to incoming/
        target = Path("../incoming") / pdf.name

        if link_path.exists() or link_path.is_symlink():
            skipped += 1
            continue

        link_path.symlink_to(target)
        click.echo(f"  {link_name}")
        created += 1

    click.echo(f"\nCreated {created} symlinks, {skipped} already existed.")
    if unrecognized:
        click.echo(f"\nUnrecognized filenames ({len(unrecognized)}) — no symlink created:")
        for f in unrecognized:
            click.echo(f"  {f}")


if __name__ == "__main__":
    main()
