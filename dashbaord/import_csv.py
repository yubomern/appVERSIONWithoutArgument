#!/usr/bin/env python3
"""
Quick script to import crash_report.csv into SQLite database.
Usage: python import_csv.py [path_to_csv]
"""

import sys
import os
from pathlib import Path

# Resolve paths relative to THIS file, not the working directory
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = SCRIPT_DIR.parent
DATABASE_DIR = PROJECT_ROOT / "database"

# Add database dir to path so 'from database import ...' works from anywhere
sys.path.insert(0, str(DATABASE_DIR))

from database import CrashDatabase


def main():
    # Default paths
    csv_path = PROJECT_ROOT / "crash_simulator" / "build" / "crash_report.csv"
    db_path = DATABASE_DIR / "crash_dumps.db"

    # Override from command line
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])

    print(f"📂 CSV Path: {csv_path}")
    print(f"💾 DB Path:  {db_path}")

    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        sys.exit(1)

    try:
        db = CrashDatabase(str(db_path))
        print("✅ Database initialized")

        # Show rows already present
        before = db.get_stats().get('total', 0)
        print(f"ℹ️  Crashes already in DB: {before}")

        count = db.import_from_crash_simulator_csv(str(csv_path))
        print(f"🎉 Successfully imported {count} crashes!")

        # Show updated stats
        stats = db.get_stats()
        print(f"\n📊 Database Stats:")
        print(f"   Total crashes  : {stats['total']}")
        print(f"   Latest         : {stats['latest']}")
        print(f"   Severity counts: {stats['severity_counts']}")
        print(f"   Category counts: {stats['category_counts']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
