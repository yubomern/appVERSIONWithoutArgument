#!/usr/bin/env python3
"""
Manage SQLite database for crash dumps.
Schema is loaded from database/schema.sql instead of hardcoded strings.
Now includes CSV import from crash_simulator.
"""

import sqlite3
import json
import os
import csv
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class CrashDatabase:
    def __init__(self, db_path: str = "crash_dumps.db"):
        self.db_path = db_path
        self.init_database()

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Execute schema.sql to create tables / indexes (idempotent)."""
        if not os.path.exists(SCHEMA_PATH):
            raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

        with open(SCHEMA_PATH, "r") as f:
            schema_sql = f.read()

        conn = self._connect()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Write - Original methods
    # ------------------------------------------------------------------ #

    def add_crash(self, crash_data: Dict) -> int:
        """Insert a crash record and its call-stack frames. Returns new id."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO crashes (
                    timestamp, unix_timestamp, type, file, line, function,
                    process_id, thread_id, stack_depth, cpu_usage,
                    memory_used_kb, memory_total_kb, probable_cause,
                    severity, confidence_score, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crash_data.get("timestamp", ""),
                    crash_data.get("unix_timestamp", 0),
                    crash_data.get("type", 0),
                    crash_data.get("file", ""),
                    crash_data.get("line", 0),
                    crash_data.get("function", ""),
                    crash_data.get("process_id", 0),
                    crash_data.get("thread_id", 0),
                    crash_data.get("stack_depth", 0),
                    crash_data.get("system_metrics", {}).get("cpu_usage_percent", 0),
                    crash_data.get("system_metrics", {}).get("memory_used_kb", 0),
                    crash_data.get("system_metrics", {}).get("memory_total_kb", 0),
                    crash_data.get("analysis", {}).get("probable_cause", ""),
                    crash_data.get("analysis", {}).get("severity", ""),
                    crash_data.get("analysis", {}).get("confidence_score", 0),
                    json.dumps(crash_data),
                ),
            )
            crash_id = cursor.lastrowid

            for idx, addr in enumerate(crash_data.get("call_stack", [])):
                cursor.execute(
                    """
                    INSERT INTO call_stack (crash_id, frame_index, address)
                    VALUES (?, ?, ?)
                    """,
                    (crash_id, idx, addr),
                )

            conn.commit()
            return crash_id
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  NEW: Import from crash_simulator CSV
    # ------------------------------------------------------------------ #

    def import_from_crash_simulator_csv(self, csv_path: str) -> int:
        """
        Import crashes from crash_simulator's crash_report.csv
        Returns number of imported records.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        imported_count = 0
        conn = self._connect()
        
        try:
            cursor = conn.cursor()
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    try:
                        # Map CSV columns to database columns
                        memory_size = int(row.get('memory_size', 0))
                        # memory_size is in bytes from simulator; convert to KB
                        memory_used_kb = max(1, memory_size // 1024) if memory_size > 0 else 1024
                        memory_total_kb = memory_used_kb * 4  # estimate: used is ~25% of total
                        category = int(row.get('category', 0))
                        cursor.execute("""
                            INSERT INTO crashes (
                                timestamp, unix_timestamp, type, category_name,
                                seed, description, call_chain_depth, exception_code,
                                intensity, recursion_depth, memory_size,
                                random_mode, generate_minidump,
                                process_id, thread_id, stack_depth,
                                cpu_usage, memory_used_kb, memory_total_kb,
                                probable_cause, severity, confidence_score,
                                raw_json, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row.get('timestamp', ''),
                            int(row.get('unix_timestamp', 0)),
                            category,
                            row.get('category_name', ''),
                            int(row.get('seed', 0)),
                            row.get('description', ''),
                            int(row.get('call_chain_depth', 0)),
                            int(row.get('exception_code', 0)),
                            int(row.get('intensity', 0)),
                            int(row.get('recursion_depth', 0)),
                            memory_size,
                            row.get('random_mode', 'false').lower() == 'true',
                            row.get('generate_minidump', 'false').lower() == 'true',
                            0,                          # process_id (not in CSV)
                            0,                          # thread_id (not in CSV)
                            int(row.get('call_chain_depth', 0)),
                            round(10.0 + (category * 5.3) % 40, 1),  # synthetic cpu estimate
                            memory_used_kb,
                            memory_total_kb,
                            row.get('description', ''),
                            self._get_severity_from_category(category),
                            75,                         # default confidence
                            json.dumps(dict(row)),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"⚠️  Error importing row: {e}")
                        continue
            
            conn.commit()
            print(f"✅ Imported {imported_count} crashes from {csv_path}")
            return imported_count
            
        finally:
            conn.close()

    def _get_severity_from_category(self, category: int) -> str:
        """Map crash category to severity level."""
        severity_map = {
            0: "CRITICAL",   # SEGMENTATION_FAULT
            1: "HIGH",       # DIVISION_BY_ZERO
            2: "CRITICAL",   # ILLEGAL_INSTRUCTION
            3: "CRITICAL",   # STACK_OVERFLOW
            4: "CRITICAL",   # HEAP_CORRUPTION
            5: "MEDIUM",     # DEADLOCK
            6: "HIGH",       # ASSERTION_FAILURE
            7: "HIGH",       # RANDOM_MATH_FAULT
            8: "HIGH",       # SYSTEM_CALL_FAILURE
            9: "CRITICAL",   # ACCESS_VIOLATION
            10: "MEDIUM",    # INVALID_HANDLE
            11: "CRITICAL",  # STACK_BUFFER_OVERFLOW
        }
        return severity_map.get(category, "LOW")

    def clear_all_crashes(self):
        """Delete all crashes from database (use with caution!)."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM call_stack")
            cursor.execute("DELETE FROM crashes")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Read - Enhanced methods
    # ------------------------------------------------------------------ #

    def get_all_crashes(self, limit: int = 200) -> List[Dict]:
        """Return crashes ordered newest-first."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM crashes ORDER BY unix_timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_crash_by_id(self, crash_id: int) -> Optional[Dict]:
        """Return a single crash record or None."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crashes WHERE id = ?", (crash_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_call_stack(self, crash_id: int) -> List[Dict]:
        """Return call-stack frames for a crash."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM call_stack WHERE crash_id = ? ORDER BY frame_index",
                (crash_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_severity_counts(self) -> Dict[str, int]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT severity, COUNT(*) as cnt FROM crashes GROUP BY severity"
            )
            return {row["severity"]: row["cnt"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_type_counts(self) -> Dict[int, int]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT type, COUNT(*) as cnt FROM crashes GROUP BY type"
            )
            return {row["type"]: row["cnt"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_category_counts(self) -> Dict[str, int]:
        """Get crash counts by category_name."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category_name, COUNT(*) as cnt FROM crashes GROUP BY category_name"
            )
            return {row["category_name"]: row["cnt"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_crashes_by_day(self) -> List[Dict]:
        """Return crash counts grouped by calendar day."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS cnt
                FROM crashes
                GROUP BY day
                ORDER BY day
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        """Return high-level stats dict."""
        crashes = self.get_all_crashes(limit=1000)
        severity_counts = self.get_severity_counts()
        category_counts = self.get_category_counts()
        latest = crashes[0]["timestamp"] if crashes else "N/A"
        return {
            "total": len(crashes),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "latest": latest,
        }

    def get_crashes_timeline(self) -> List[Dict]:
        """Return crash counts per hour for timeline chart."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    substr(timestamp, 1, 13) || ':00:00' AS hour_slot,
                    COUNT(*) AS cnt,
                    SUM(CASE WHEN severity='CRITICAL' THEN 1 ELSE 0 END) AS critical_cnt,
                    SUM(CASE WHEN severity='HIGH'     THEN 1 ELSE 0 END) AS high_cnt,
                    AVG(cpu_usage)     AS avg_cpu,
                    AVG(memory_used_kb) AS avg_mem_kb
                FROM crashes
                GROUP BY hour_slot
                ORDER BY hour_slot
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_crashes_for_dashboard(self, limit: int = 1000) -> List[Dict]:
        """
        Get crashes formatted for dashboard display.
        Maps database fields to dashboard expected fields.
        """
        crashes = self.get_all_crashes(limit)
        
        # Map to dashboard format
        dashboard_crashes = []
        for crash in crashes:
            dashboard_crash = {
                'timestamp': crash['timestamp'],
                'unix_timestamp': crash['unix_timestamp'],
                'fault_type': crash['type'],
                'fault_name': crash.get('category_name', f"Type {crash['type']}"),
                'file': crash.get('file', ''),
                'line': crash.get('line', 0),
                'function': crash.get('function', ''),
                'process_id': crash.get('process_id', 0),
                'thread_id': crash.get('thread_id', 0),
                'stack_depth': crash.get('stack_depth', 0),
                'cpu_usage_percent': crash.get('cpu_usage', 0.0),
                'memory_used_kb': crash.get('memory_used_kb', 0),
                'memory_total_kb': crash.get('memory_total_kb', 0),
                'memory_used_mb': crash.get('memory_used_kb', 0) / 1024,
                'memory_total_mb': crash.get('memory_total_kb', 0) / 1024,
                'thread_count': 1,  # default
                'process_name': 'Crash Simulator',
                'probable_cause': crash.get('probable_cause', crash.get('description', '')),
                'severity': crash.get('severity', 'LOW'),
                'recommendation': '',
                'confidence_score': crash.get('confidence_score', 0),
            }
            dashboard_crashes.append(dashboard_crash)
        
        return dashboard_crashes