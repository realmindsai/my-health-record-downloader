# ABOUTME: CLI tool to query the medical test results SQLite database.
# ABOUTME: Supports querying by test name, panel, date, and tracking trends over time.

import sqlite3
import click
from pathlib import Path

DB_PATH = Path(__file__).parent / "personal" / "medical_results.db"


def get_conn():
    if not DB_PATH.exists():
        click.echo(f"Database not found at {DB_PATH}. Run build_test_db.py first.")
        raise SystemExit(1)
    return sqlite3.connect(DB_PATH)


@click.group()
def cli():
    """Query medical test results database."""
    pass


@cli.command()
def panels():
    """List all test panels."""
    conn = get_conn()
    for row in conn.execute(
        "SELECT test_panel, COUNT(DISTINCT test_name), COUNT(DISTINCT collected_date) "
        "FROM test_results GROUP BY test_panel ORDER BY test_panel"
    ):
        click.echo(f"  {row[0]:35s} {row[1]:3d} tests across {row[2]} dates")
    conn.close()


@cli.command()
@click.argument("panel", required=False)
def tests(panel):
    """List all test names, optionally filtered by panel."""
    conn = get_conn()
    if panel:
        rows = conn.execute(
            "SELECT DISTINCT test_name, units, test_panel FROM test_results "
            "WHERE test_panel LIKE ? ORDER BY test_name",
            (f"%{panel}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT test_name, units, test_panel FROM test_results "
            "ORDER BY test_panel, test_name"
        ).fetchall()
    for row in rows:
        click.echo(f"  {row[2]:30s}  {row[0]:35s} ({row[1] or 'N/A'})")
    conn.close()


@cli.command()
def dates():
    """List all collection dates with test counts."""
    conn = get_conn()
    for row in conn.execute(
        "SELECT collected_date, laboratory, COUNT(*) "
        "FROM test_results GROUP BY collected_date, laboratory "
        "ORDER BY collected_date"
    ):
        click.echo(f"  {row[0]}  {row[1]:25s}  ({row[2]} tests)")
    conn.close()


@cli.command()
@click.argument("name")
def trend(name):
    """Show all results for a test over time (fuzzy match on name)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT collected_date, value, value_text, units, ref_range_text, is_abnormal "
        "FROM test_results WHERE test_name LIKE ? ORDER BY collected_date",
        (f"%{name}%",)
    ).fetchall()
    if not rows:
        click.echo(f"No results found matching '{name}'")
        conn.close()
        return

    test_name = conn.execute(
        "SELECT DISTINCT test_name FROM test_results WHERE test_name LIKE ?",
        (f"%{name}%",)
    ).fetchall()
    click.echo(f"\nTrend for: {', '.join(t[0] for t in test_name)}")
    click.echo(f"{'Date':12s} {'Value':>10s} {'Units':15s} {'Ref Range':20s} {'Status':8s}")
    click.echo("-" * 70)
    for row in rows:
        status = "ABNORMAL" if row[5] else "normal"
        click.echo(f"  {row[0]:10s} {row[2]:>10s} {row[3] or '':15s} {row[4] or '':20s} {status:8s}")
    conn.close()


@cli.command()
@click.argument("date")
def date(date):
    """Show all results for a specific collection date (partial match)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT test_panel, test_name, value_text, units, ref_range_text, is_abnormal "
        "FROM test_results WHERE collected_date LIKE ? "
        "ORDER BY test_panel, test_name",
        (f"%{date}%",)
    ).fetchall()
    if not rows:
        click.echo(f"No results for date matching '{date}'")
        conn.close()
        return

    current_panel = None
    for row in rows:
        if row[0] != current_panel:
            current_panel = row[0]
            click.echo(f"\n  === {current_panel} ===")
        flag = " ** ABNORMAL" if row[5] else ""
        click.echo(f"    {row[1]:35s} {row[2]:>10s} {row[3] or '':15s} {row[4] or '':20s}{flag}")
    conn.close()


@cli.command()
def abnormal():
    """Show all abnormal results."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT collected_date, test_panel, test_name, value_text, units, ref_range_text "
        "FROM test_results WHERE is_abnormal = 1 ORDER BY collected_date"
    ).fetchall()
    click.echo(f"\n  {len(rows)} abnormal results found:\n")
    for row in rows:
        click.echo(f"  {row[0]}  {row[2]:35s} = {row[3]:>8s} {row[4] or '':15s} Ref: {row[5] or ''}")
    conn.close()


@cli.command()
def imaging():
    """Show all imaging reports."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT exam_date, exam_type, laboratory, referring_doctor, reporting_doctor, "
        "clinical_notes, findings, conclusion FROM imaging_reports ORDER BY exam_date"
    ).fetchall()
    for row in rows:
        click.echo(f"\n{'='*70}")
        click.echo(f"  Date:       {row[0]}")
        click.echo(f"  Type:       {row[1]}")
        click.echo(f"  Lab:        {row[2]}")
        click.echo(f"  Referred:   {row[3]}")
        click.echo(f"  Reported:   {row[4]}")
        click.echo(f"  Clinical:   {row[5]}")
        click.echo(f"  Findings:   {row[6]}")
        click.echo(f"  Conclusion: {row[7]}")
    conn.close()


@cli.command()
@click.argument("panel")
def panel(panel):
    """Show the latest results for a specific panel (fuzzy match)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT t1.collected_date, t1.test_name, t1.value_text, t1.units, "
        "t1.ref_range_text, t1.is_abnormal "
        "FROM test_results t1 "
        "INNER JOIN ("
        "  SELECT test_name, MAX(collected_date) as max_date "
        "  FROM test_results WHERE test_panel LIKE ? "
        "  GROUP BY test_name"
        ") t2 ON t1.test_name = t2.test_name AND t1.collected_date = t2.max_date "
        "WHERE t1.test_panel LIKE ? "
        "ORDER BY t1.test_name",
        (f"%{panel}%", f"%{panel}%")
    ).fetchall()
    if not rows:
        click.echo(f"No panel matching '{panel}'")
        conn.close()
        return

    click.echo(f"\n  Latest results for panel matching '{panel}':\n")
    for row in rows:
        flag = " ** ABNORMAL" if row[5] else ""
        click.echo(f"  {row[0]}  {row[1]:35s} {row[2]:>10s} {row[3] or '':15s} {row[4] or '':20s}{flag}")
    conn.close()


@cli.command()
def summary():
    """Show a comprehensive summary of latest results across all panels."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT t1.test_panel, t1.collected_date, t1.test_name, t1.value_text, "
        "t1.units, t1.ref_range_text, t1.is_abnormal "
        "FROM test_results t1 "
        "INNER JOIN ("
        "  SELECT test_name, MAX(collected_date) as max_date "
        "  FROM test_results GROUP BY test_name"
        ") t2 ON t1.test_name = t2.test_name AND t1.collected_date = t2.max_date "
        "WHERE t1.value IS NOT NULL OR t1.value_text IS NOT NULL "
        "ORDER BY t1.test_panel, t1.test_name"
    ).fetchall()

    current_panel = None
    for row in rows:
        if row[0] != current_panel:
            current_panel = row[0]
            click.echo(f"\n  === {current_panel} ===")
        flag = " **" if row[6] else ""
        click.echo(f"    [{row[1]}] {row[2]:35s} {row[3]:>10s} {row[4] or '':12s} {row[5] or '':20s}{flag}")
    conn.close()


if __name__ == "__main__":
    cli()
