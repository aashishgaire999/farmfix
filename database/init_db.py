#!/usr/bin/env python3
"""
init_db.py — create (or rebuild) the FarmFix SQLite3 database.

COMP 368 Database Systems, Project 1
Team: Ayush Gaire, Ashish Gaire, AJ Rayamajhi

Usage (from the project root):
    python database/init_db.py

This script demonstrates the two most basic SQLite3 skills the assignment
asks for:
  1. Creating / opening a database file  -> sqlite3.connect(...)
  2. Running a .sql script against it    -> connection.executescript(...)

Running it twice is safe: schema.sql starts with DROP TABLE IF EXISTS, so
the database is rebuilt from scratch every time.
"""

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "farmfix.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")
DATA_PATH = os.path.join(HERE, "sample_data.sql")


def run_script(conn, path, label):
    with open(path, "r", encoding="utf-8") as handle:
        conn.executescript(handle.read())
    print(f"  [ok] applied {label} ({os.path.basename(path)})")


def main():
    fresh = not os.path.exists(DB_PATH)
    print("FarmFix database initialisation")
    print(f"  target : {DB_PATH}")
    print(f"  status : {'creating new file' if fresh else 'rebuilding existing file'}")

    # sqlite3.connect() CREATES the file if it does not already exist.
    # No server to start, no host, no port, no username or password --
    # this is the main practical difference from MySQL or PostgreSQL.
    conn = sqlite3.connect(DB_PATH)
    try:
        # SQLite ships with foreign key enforcement OFF for backwards
        # compatibility. It must be switched on for every connection.
        conn.execute("PRAGMA foreign_keys = ON;")

        run_script(conn, SCHEMA_PATH, "schema")
        run_script(conn, DATA_PATH, "sample data")
        conn.commit()

        # ---- schema inspection: prove the tables really exist -------------
        print("\n  Tables created (read back from sqlite_master):")
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for (name,) in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            fks = conn.execute(f"PRAGMA foreign_key_list({name})").fetchall()
            print(
                f"    - {name:<12} {len(cols)} columns, "
                f"{len(fks)} foreign key(s), {count} row(s)"
            )

        print("\n  Foreign key integrity check:", end=" ")
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        print("clean" if not problems else f"{len(problems)} PROBLEM(S) {problems}")

        total_repair = conn.execute("SELECT ROUND(SUM(cost),2) FROM repairs").fetchone()[0]
        total_maint = conn.execute("SELECT ROUND(SUM(cost),2) FROM maintenance").fetchone()[0]
        print(f"\n  Seeded totals: repairs ${total_repair:,.2f} | "
              f"maintenance ${total_maint:,.2f}")

        print("\nDone. Start the app with:  python app.py")
    except sqlite3.Error as exc:
        print(f"\n  SQLite error: {exc}", file=sys.stderr)
        conn.rollback()
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
