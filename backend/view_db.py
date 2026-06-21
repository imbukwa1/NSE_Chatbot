"""Read-only SQLite database viewer for local development.

Usage examples:
    python view_db.py
    python view_db.py users
    python view_db.py stocks --limit 20
"""

import argparse
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data" / "nse_stocks.db"
SENSITIVE_COLUMN_PARTS = ("password", "token", "secret", "api_key")


def fetch_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def quote_identifier(identifier):
    """Quote a SQLite identifier after table-name validation."""
    return '"' + identifier.replace('"', '""') + '"'


def print_table(rows):
    if not rows:
        print("No records found.")
        return

    columns = rows[0].keys()
    display_rows = [
        {
            column: (
                "[hidden]"
                if any(part in column.lower() for part in SENSITIVE_COLUMN_PARTS)
                else row[column]
            )
            for column in columns
        }
        for row in rows
    ]

    widths = {
        column: max(len(column), *(len(str(row[column])) for row in display_rows))
        for column in columns
    }

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    print(header)
    print(separator)

    for row in display_rows:
        print(" | ".join(str(row[column]).ljust(widths[column]) for column in columns))


def main():
    parser = argparse.ArgumentParser(description="View local NSE Chatbot SQLite records.")
    parser.add_argument("table", nargs="?", help="Table name to preview.")
    parser.add_argument("--limit", type=int, default=10, help="Number of rows to show.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        tables = fetch_tables(conn)
        if not args.table:
            print(f"Database: {DB_PATH}")
            print("\nTables:")
            for table in tables:
                count = conn.execute(
                    f"SELECT COUNT(*) AS total FROM {quote_identifier(table)}"
                ).fetchone()["total"]
                print(f"- {table} ({count} records)")
            print("\nRun: python view_db.py <table_name> --limit 20")
            return

        if args.table not in tables:
            print(f"Table not found: {args.table}")
            print("Available tables:", ", ".join(tables))
            raise SystemExit(1)

        rows = conn.execute(
            f"SELECT * FROM {quote_identifier(args.table)} LIMIT ?",
            (max(args.limit, 1),),
        ).fetchall()
        print(f"Database: {DB_PATH}")
        print(f"Table: {args.table}")
        print_table(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
