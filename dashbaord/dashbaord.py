#!/usr/bin/env python3
"""
Crash Investigator Dashboard v3.0
- Fixed CSV parsing (handles embedded comma in timestamp+unix_timestamp field)
- Added Crash Analyzer tab (rule-based + heuristic engine in Python)
- Added Crash Simulator tab (trigger & visualize any of 10 fault types)
- Added Diag class panel, Sequence diagram, Use Case descriptions
ACTIA PFE 2026 – Doua Ghriss
"""



import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO


# ─── Page config - MUST BE FIRST! ────────────────────────────────────────────
st.set_page_config(
    page_title="Crash Investigator Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Import Database Module ──────────────────────────────────────────────────
import sys
sys.path.append(str(Path(__file__).parent.parent / "database"))

try:
    from database import CrashDatabase
    DB_INITIALIZED = True
except ImportError as e:
    DB_INITIALIZED = False
    CrashDatabase = None

# Initialize database connection
DB_PATH = Path(__file__).parent.parent / "database" / "crash_dumps.db"
CSV_PATH = Path(__file__).parent.parent / "crash_simulator" / "build" / "crash_report.csv"
def auto_sync_csv_to_db():
    """Importe automatiquement le CSV si la base est vide ou obsolète."""
    if not CSV_PATH.exists() or not DB_INITIALIZED or not db:
        return
    try:
        # Compter les lignes réelles dans le CSV (moins l'en-tête)
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_rows = sum(1 for _ in f) - 1
        
        db_rows = db.get_stats().get('total', 0)
        
        if csv_rows > db_rows:
            db.import_from_crash_simulator_csv(str(CSV_PATH))
            st.success(f"🔄 Auto-import : {csv_rows - db_rows} nouveaux crashs ajoutés à la base.")
    except Exception as e:
        st.warning(f"⚠️ Sync auto échouée : {e}")
db = None
if DB_INITIALIZED:
    try:
        db = CrashDatabase(str(DB_PATH))
        st.session_state['db'] = db
    except Exception as e:
        # Don't use st.error() here - we'll show it in sidebar instead
        db = None

# Rest of imports and constants...
DASHBOARD_DIR = Path(__file__).parent

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem; border-radius: 10px; color: white; text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .severity-CRITICAL { background-color:#dc3545;color:white;padding:2px 8px;border-radius:5px;font-weight:bold;display:inline-block; }
    .severity-HIGH     { background-color:#fd7e14;color:white;padding:2px 8px;border-radius:5px;font-weight:bold;display:inline-block; }
    .severity-MEDIUM   { background-color:#ffc107;color:black;padding:2px 8px;border-radius:5px;font-weight:bold;display:inline-block; }
    .severity-LOW      { background-color:#28a745;color:white;padding:2px 8px;border-radius:5px;font-weight:bold;display:inline-block; }
    .section-header    { border-left:4px solid #FF4B4B;padding-left:1rem;margin:1rem 0; }
    .diag-box { background:#1e1e1e;color:#c5e1a5;font-family:'Courier New',monospace;
                padding:1rem;border-radius:8px;border-left:3px solid #FF4B4B;
                white-space:pre;overflow-x:auto;font-size:0.8rem;margin:0.5rem 0; }
    .sim-card { background:linear-gradient(135deg,#1a1a2e,#16213e);color:#e0e0e0;
                padding:1rem;border-radius:10px;border:1px solid #333;margin:0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
FAULT_MAP = {
    0: "SIGABRT (Abort Signal) - Original Test",
    1: "SIGSEGV (Null Pointer Dereference)",
    2: "Stack Overflow",
    3: "Invalid Memory Access",
    4: "Windows Exception (SEH)",
    5: "SIGFPE (Arithmetic Exception)",
    6: "SIGILL (Illegal Instruction)",
    7: "SIGBUS (Bus Error)",
    8: "SIGTRAP (Trace Trap)",
    9: "SIGSYS (Bad System Call)",
    10: "Heap Corruption",
}

SEVERITY_COLORS = {
    "CRITICAL": "#dc3545",
    "HIGH":     "#fd7e14",
    "MEDIUM":   "#ffc107",
    "LOW":      "#28a745",
}

# ─────────────────────────────────────────────────────────────────────────────
#  CSV LOADER  – fixes the embedded-comma bug in the C++ exporter output
#  The C++ CsvCrashExporter writes the timestamp WITHOUT quotes but
#  unix_timestamp as a plain number after a comma, which is fine.
#  However older builds wrapped "timestamp,unix_timestamp" in one quoted field.
#  This loader handles BOTH formats automatically.
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_csv(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        return pd.DataFrame()

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        st.error(f"Cannot read file: {e}")
        return pd.DataFrame()

    # ── Detect the "broken" format where timestamp+unix_ts share one quoted cell
    #    Pattern: "2026-04-04 03:02:59,1775264579,3,...
    broken_pattern = re.compile(
        r'^"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+),', re.MULTILINE
    )

    lines = raw.splitlines()
    fixed_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            # Always pass the header through unchanged
            fixed_lines.append(line)
            header_done = True
            continue

        m = broken_pattern.match(line)
        if m:
            # Remove the leading quote, split the merged cell
            line = line[1:]  # drop opening "
            # Find the matching close of the merged field (next unescaped quote)
            # The merged field ends after unix_timestamp: "ts,unix," → ts,unix,
            # Simplest: replace first ," with , to close the merged cell properly
            # Actually the format is: "ts,unix,fault_type,...,"HIGH",...
            # We just need to remove the outer quotes around ts,unix
            line = re.sub(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+),', 
                          lambda mm: mm.group(1) + ',' + mm.group(2) + ',', line)
            # Strip trailing quote that closed the merged field (if present)
            # The broken CSV ends data rows with ,"value" and the last field
            # may still have a stray quote – clean up doubled quotes
            line = line.replace('""', '"')
            # Remove any remaining outer quote from this line
            if line.endswith('"') and line.count('"') % 2 == 1:
                line = line[:-1]
        fixed_lines.append(line)

    fixed_csv = "\n".join(fixed_lines)

    try:
        df = pd.read_csv(StringIO(fixed_csv), quotechar='"', sep=',',
                         on_bad_lines='warn', engine='python')
    except Exception:
        # Fallback: try without quoting
        try:
            df = pd.read_csv(StringIO(fixed_csv), sep=',', on_bad_lines='skip')
        except Exception as e2:
            st.error(f"CSV parse failed: {e2}")
            return pd.DataFrame()

    # ── Normalise column names ────────────────────────────────────────────────
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # ── Clean string columns ──────────────────────────────────────────────────
    for col in df.select_dtypes(include='object').columns:
        df[col] = (df[col].astype(str)
                          .str.strip('"\'')
                          .str.strip()
                          .replace(['nan', 'NaN', 'None', ''], np.nan))

    # ── Parse timestamp ───────────────────────────────────────────────────────
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'],
                                         format='%Y-%m-%d %H:%M:%S',
                                         errors='coerce')
        df['date']        = df['timestamp'].dt.date
        df['hour']        = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()

    # ── Numeric coercions ─────────────────────────────────────────────────────
    num_cols = ['unix_timestamp', 'fault_type', 'line', 'process_id',
                'thread_id', 'stack_depth', 'cpu_usage_percent',
                'memory_used_kb', 'memory_total_kb', 'thread_count',
                'confidence_score']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ── Derived columns ───────────────────────────────────────────────────────
    if 'fault_type' in df.columns:
        df['fault_name'] = df['fault_type'].apply(
            lambda x: FAULT_MAP.get(int(x), f"Type {int(x)}") if pd.notna(x) else "Unknown"
        )
    if 'memory_used_kb' in df.columns:
        df['memory_used_mb']  = df['memory_used_kb']  / 1024
    if 'memory_total_kb' in df.columns:
        df['memory_total_mb'] = df['memory_total_kb'] / 1024
        if 'memory_used_kb' in df.columns:
            df['memory_usage_pct'] = (
                df['memory_used_kb'] / df['memory_total_kb'] * 100
            ).round(1)

    # ── Drop rows where timestamp is completely unparseable ───────────────────
    if 'timestamp' in df.columns:
        df = df.dropna(subset=['timestamp'])

    return df.reset_index(drop=True)


def normalize_any_csv(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Bring any CSV schema into the common crash-dashboard schema."""
    if df.empty:
        return df
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # ── test_crash_results / test_crash_analyzer schema ──────────────────
    if 'test_id' in df.columns and 'fault_type' not in df.columns:
        df['fault_type'] = df['test_id']
    if 'description' in df.columns and 'probable_cause' not in df.columns:
        df['probable_cause'] = df['description']
    if 'test_name' in df.columns and 'process_name' not in df.columns:
        df['process_name'] = df['test_name']
    if 'severity' in df.columns:
        sev_map = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL'}
        df['severity'] = df['severity'].apply(
            lambda v: sev_map.get(v, v) if isinstance(v, int) else v
        )

    # ── fill required columns with sensible defaults ──────────────────────
    defaults = {
        'unix_timestamp': 0, 'fault_type': 0, 'file': source_name,
        'line': 0, 'function': '', 'process_id': 0, 'thread_id': 0,
        'stack_depth': 0, 'cpu_usage_percent': 0.0,
        'memory_used_kb': 0, 'memory_total_kb': 0, 'thread_count': 1,
        'process_name': source_name, 'probable_cause': '',
        'severity': 'LOW', 'recommendation': '', 'confidence_score': 0,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    # ── timestamp ─────────────────────────────────────────────────────────
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date']        = df['timestamp'].dt.date
        df['hour']        = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()

    # ── numerics ──────────────────────────────────────────────────────────
    for col in ['fault_type', 'cpu_usage_percent', 'memory_used_kb',
                'memory_total_kb', 'confidence_score', 'stack_depth',
                'thread_count', 'process_id', 'thread_id', 'unix_timestamp']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ── derived columns ───────────────────────────────────────────────────
    if 'fault_type' in df.columns:
        df['fault_name'] = df['fault_type'].apply(
            lambda x: FAULT_MAP.get(int(x), f'Type {int(x)}') if pd.notna(x) else 'Unknown'
        )
    if 'memory_used_kb' in df.columns:
        df['memory_used_mb']  = df['memory_used_kb']  / 1024
    if 'memory_total_kb' in df.columns:
        df['memory_total_mb'] = df['memory_total_kb'] / 1024
        if 'memory_used_kb' in df.columns:
            df['memory_usage_pct'] = (
                df['memory_used_kb'] / df['memory_total_kb'].replace(0, np.nan) * 100
            ).round(1)

    df['_source'] = source_name
    return df.dropna(subset=['timestamp']) if 'timestamp' in df.columns else df


def discover_csv_files() -> list:
    """Return all CSV files found in the dashboard folder and crash_simulator/build."""
    found = []
    # Dashboard folder itself
    for p in DASHBOARD_DIR.glob("*.csv"):
        found.append(p)
    # crash_simulator build output
    sim_csv = CSV_PATH  # already defined as crash_simulator/build/crash_report.csv
    if sim_csv.exists() and sim_csv not in found:
        found.append(sim_csv)
    return found


@st.cache_data(ttl=60)
def load_all_csvs() -> dict[str, pd.DataFrame]:
    """Load every CSV in the dashboard folder; return {filename: DataFrame}."""
    result: dict[str, pd.DataFrame] = {}
    for csv_path in discover_csv_files():
        # Use the specialised loader for crash_dump.csv (handles broken format)
        if csv_path.name == 'crash_dump.csv':
            df = load_csv(csv_path)
        else:
            try:
                df = pd.read_csv(csv_path, on_bad_lines='skip')
            except Exception:
                df = pd.DataFrame()
        if not df.empty:
            result[csv_path.name] = normalize_any_csv(df, csv_path.name)
    return result

@st.cache_data(ttl=60)
def load_data_from_database() -> pd.DataFrame:
    """Load crashes from SQLite database."""
    try:
        db = st.session_state.get('db')
        if not db:
            return pd.DataFrame()

        crashes = db.get_crashes_for_dashboard(limit=1000)
        if not crashes:
            return pd.DataFrame()

        df = pd.DataFrame(crashes)

        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()

        # Derived columns
        if 'memory_used_kb' in df.columns and 'memory_total_kb' in df.columns:
            df['memory_used_mb']  = (df['memory_used_kb']  / 1024).round(2)
            df['memory_total_mb'] = (df['memory_total_kb'] / 1024).round(2)
            df['memory_usage_pct'] = (
                df['memory_used_kb'] / df['memory_total_kb'].replace(0, np.nan) * 100
            ).round(1)

        return df.dropna(subset=['timestamp']) if 'timestamp' in df.columns else df

    except Exception as e:
        st.error(f"❌ Error loading from database: {e}")
        return pd.DataFrame()


# ── Sidebar - Database Import Section ──────────────────────────────────────
with st.sidebar:
    st.markdown("## 📥 Database Management")

    if CSV_PATH.exists():
        st.caption(f"📄 CSV: `{CSV_PATH.name}`")
        if st.button("📤 Import CSV → Database", type="primary", use_container_width=True):
            try:
                db = st.session_state.get('db')
                if db:
                    with st.spinner("Importing crashes..."):
                        count = db.import_from_crash_simulator_csv(str(CSV_PATH))
                    st.success(f"✅ Imported {count} crashes!")
                    st.rerun()
                else:
                    st.error("❌ Database not initialized")
            except Exception as e:
                st.error(f"❌ Import failed: {e}")
    else:
        st.warning(f"⚠️ CSV not found:\n`{CSV_PATH}`")

    st.markdown("---")

    # Database stats – severity breakdown
    try:
        db = st.session_state.get('db')
        if db:
            stats = db.get_stats()
            total = stats.get('total', 0)
            st.metric("📊 Total in Database", total)
            if total > 0:
                sev = stats.get('severity_counts', {})
                c1, c2 = st.columns(2)
                c1.metric("🔴 Critical", sev.get('CRITICAL', 0))
                c2.metric("🟠 High",     sev.get('HIGH', 0))
                c3, c4 = st.columns(2)
                c3.metric("🟡 Medium",   sev.get('MEDIUM', 0))
                c4.metric("🟢 Low",      sev.get('LOW', 0))
                st.caption(f"🕐 Latest: {stats.get('latest', 'N/A')}")
    except:
        pass

    st.markdown("---")







def load_data() -> pd.DataFrame:
    """
    Main data loader - tries database first, falls back to CSV files.
    """
    # Try database first
    df_db = load_data_from_database()
    if not df_db.empty:
        st.success(f"✅ Loaded {len(df_db)} crashes from database")
        return df_db
    
    # Fallback to CSV files
    st.info("📂 No data in database, loading from CSV files...")
    all_dfs = load_all_csvs()
    if not all_dfs:
        st.warning(f"⚠️ No CSV files found in `{DASHBOARD_DIR}`")
        return pd.DataFrame()
    merged = pd.concat(all_dfs.values(), ignore_index=True)
    dedup_cols = [c for c in ['timestamp', 'fault_type', 'process_name'] if c in merged.columns]
    if dedup_cols:
        merged = merged.drop_duplicates(subset=dedup_cols, keep='last')
    if 'timestamp' in merged.columns:
        merged = merged.sort_values('timestamp', na_position='last')
    return merged.reset_index(drop=True)
# ─────────────────────────────────────────────────────────────────────────────
#  PYTHON CRASH ANALYZER  (rule-based heuristic engine)
# ─────────────────────────────────────────────────────────────────────────────

ANALYSIS_RULES = {
    1: {
        "probable_cause": "Hardware Exception – divide-by-zero or arithmetic overflow",
        "severity":       "HIGH",
        "recommendation": "Validate all divisors; use SafeDivide wrapper; enable -ftrapv",
        "confidence":     80,
    },
    2: {
        "probable_cause": "Segmentation Fault – null/wild pointer or out-of-bounds access",
        "severity":       "CRITICAL",
        "recommendation": "Enable AddressSanitizer (-fsanitize=address); validate every pointer before dereference",
        "confidence":     85,
    },
    3: {
        "probable_cause": "Abort Signal – std::abort() or failed assert()",
        "severity":       "HIGH",
        "recommendation": "Search for assert() / abort() calls near the reported file:line; review exception handling",
        "confidence":     75,
    },
    4: {
        "probable_cause": "Illegal Instruction – corrupt binary or CPU mismatch",
        "severity":       "CRITICAL",
        "recommendation": "Verify binary integrity (sha256); check -march flag matches target CPU",
        "confidence":     90,
    },
    5: {
        "probable_cause": "Bus Error – misaligned memory access or bad mmap region",
        "severity":       "HIGH",
        "recommendation": "Check struct packing / alignment attributes; validate mmap() return values",
        "confidence":     82,
    },
    6: {
        "probable_cause": "Trace Trap – unexpected breakpoint or SIGTRAP in code",
        "severity":       "MEDIUM",
        "recommendation": "Search for __debugbreak() / int3 in source; check ptrace interaction",
        "confidence":     70,
    },
    7: {
        "probable_cause": "Bad System Call – invalid syscall number or bad argument",
        "severity":       "HIGH",
        "recommendation": "Review seccomp filters and syscall wrappers; validate all pointer arguments to syscalls",
        "confidence":     78,
    },
    8: {
        "probable_cause": "Stack Overflow – infinite recursion or oversized stack frame",
        "severity":       "CRITICAL",
        "recommendation": "Add recursion depth limit; reduce stack-allocated buffers; increase ulimit -s if needed",
        "confidence":     88,
    },
    9: {
        "probable_cause": "Heap Corruption – allocator canary or metadata overwritten",
        "severity":       "CRITICAL",
        "recommendation": "Run with valgrind --tool=memcheck or -fsanitize=address to pinpoint the write",
        "confidence":     92,
    },
    10: {
        "probable_cause": "Double Free – free() called twice on the same pointer",
        "severity":       "CRITICAL",
        "recommendation": "Null-out pointers after free(); prefer unique_ptr / RAII wrappers",
        "confidence":     95,
    },
}


def python_analyze(fault_type: int,
                   cpu_pct: float,
                   mem_used_kb: float,
                   mem_total_kb: float) -> dict:
    """Pure-Python heuristic analyzer mirroring the C++ Analyze() logic."""
    rule = ANALYSIS_RULES.get(fault_type, {
        "probable_cause": "Unknown cause",
        "severity":       "LOW",
        "recommendation": "Manual investigation required",
        "confidence":     50,
    })
    result = dict(rule)

    # Memory heuristic
    if mem_total_kb > 0:
        pct = mem_used_kb / mem_total_kb * 100
        if pct > 90:
            result["probable_cause"] += " + Memory exhaustion suspected"
            result["confidence"] = min(result["confidence"] + 10, 100)

    # CPU heuristic
    if cpu_pct > 90:
        result["probable_cause"] += " + High CPU load at crash time"
        result["confidence"] = min(result["confidence"] + 5, 100)

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  CRASH SIMULATOR  (Python-side, writes to crash_dump.csv)
# ─────────────────────────────────────────────────────────────────────────────

SIM_SCENARIOS = [
    {"id": 1,  "name": "NULL Dereference",        "signal": "SIGSEGV", "fault_type": 2,
     "desc": "Dereferences a null pointer",             "cpu_range": (5, 40),  "mem_range": (0.3, 0.6)},
    {"id": 2,  "name": "Stack Out-of-Bounds",      "signal": "SIGSEGV", "fault_type": 2,
     "desc": "Reads past end of stack array",           "cpu_range": (10, 50), "mem_range": (0.3, 0.6)},
    {"id": 3,  "name": "Use-After-Free",           "signal": "SIGSEGV", "fault_type": 2,
     "desc": "Accesses freed memory",                   "cpu_range": (20, 60), "mem_range": (0.4, 0.7)},
    {"id": 4,  "name": "Wild Pointer Write",       "signal": "SIGSEGV", "fault_type": 2,
     "desc": "Writes to invalid address",               "cpu_range": (5, 30),  "mem_range": (0.3, 0.5)},
    {"id": 5,  "name": "Direct abort()",           "signal": "SIGABRT", "fault_type": 3,
     "desc": "Calls abort() directly",                  "cpu_range": (10, 45), "mem_range": (0.4, 0.7)},
    {"id": 6,  "name": "assert() Failure",         "signal": "SIGABRT", "fault_type": 3,
     "desc": "Triggers assert(false)",                  "cpu_range": (5, 35),  "mem_range": (0.3, 0.6)},
    {"id": 7,  "name": "Double Free",              "signal": "SIGABRT", "fault_type": 10,
     "desc": "free() called twice on same ptr",         "cpu_range": (15, 55), "mem_range": (0.5, 0.8)},
    {"id": 8,  "name": "Heap Corruption",          "signal": "SIGABRT", "fault_type": 9,
     "desc": "Writes past end of heap buffer",          "cpu_range": (20, 70), "mem_range": (0.6, 0.9)},
    {"id": 9,  "name": "Integer Div-by-Zero",      "signal": "SIGFPE",  "fault_type": 1,
     "desc": "Integer division by zero",                "cpu_range": (80, 99), "mem_range": (0.4, 0.7)},
    {"id": 10, "name": "Float Div-by-Zero",        "signal": "SIGFPE",  "fault_type": 1,
     "desc": "FP division by zero (FP exceptions on)",  "cpu_range": (75, 99), "mem_range": (0.4, 0.7)},
    {"id": 11, "name": "Illegal Instruction (UD2)","signal": "SIGILL",  "fault_type": 4,
     "desc": "Executes undefined CPU instruction",      "cpu_range": (10, 40), "mem_range": (0.3, 0.6)},
    {"id": 12, "name": "Misaligned Access",        "signal": "SIGBUS",  "fault_type": 5,
     "desc": "Reads int from odd address",              "cpu_range": (20, 60), "mem_range": (0.4, 0.7)},
    {"id": 13, "name": "Stack Overflow",           "signal": "SIGSEGV", "fault_type": 8,
     "desc": "Infinite recursion exhausts stack",       "cpu_range": (30, 80), "mem_range": (0.7, 0.98)},
    {"id": 14, "name": "Deep Call Chain (8 frames)","signal": "SIGABRT","fault_type": 3,
     "desc": "main→L1→…→L8→crash; tests stack capture", "cpu_range": (20, 50), "mem_range": (0.4, 0.65)},
]

MEM_TOTAL_KB = 16_553_776   # 16 GB reference system


def simulate_crash(scenario: dict, process_name: str = "CoreDumpApp") -> dict:
    """Generate a synthetic crash row matching the CSV schema."""
    now = datetime.now()
    cpu_pct = round(random.uniform(*scenario["cpu_range"]), 2)
    mem_frac = random.uniform(*scenario["mem_range"])
    mem_used_kb = int(MEM_TOTAL_KB * mem_frac)
    stack_depth = random.randint(6, 28)
    pid  = random.randint(10000, 65535)
    tid  = random.randint(10000, 65535)
    line = random.randint(10, 300)

    analysis = python_analyze(
        scenario["fault_type"], cpu_pct, mem_used_kb, MEM_TOTAL_KB
    )

    return {
        "timestamp":         now.strftime("%Y-%m-%d %H:%M:%S"),
        "unix_timestamp":    int(now.timestamp()),
        "fault_type":        scenario["fault_type"],
        "file":              f"/home/user/project/sim_{scenario['signal'].lower()}.cpp",
        "line":              line,
        "function":          f"sim_{scenario['name'].replace(' ', '_').lower()[:20]}",
        "process_id":        pid,
        "thread_id":         tid,
        "stack_depth":       stack_depth,
        "cpu_usage_percent": cpu_pct,
        "memory_used_kb":    mem_used_kb,
        "memory_total_kb":   MEM_TOTAL_KB,
        "thread_count":      random.randint(1, 12),
        "process_name":      process_name,
        "probable_cause":    analysis["probable_cause"],
        "severity":          analysis["severity"],
        "recommendation":    analysis["recommendation"],
        "confidence_score":  analysis["confidence"],
    }


def append_to_csv(row: dict, path: Path):
    df_new = pd.DataFrame([row])
    write_header = not path.exists() or path.stat().st_size == 0
    df_new.to_csv(path, mode='a', header=write_header, index=False)


# ─────────────────────────────────────────────────────────────────────────────
#  CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def pie_chart(df, col, title):
    if df.empty or col not in df.columns:
        return None
    counts = df[col].dropna().value_counts().reset_index()
    counts.columns = [col, "Count"]
    color_map = SEVERITY_COLORS if col == "severity" else None
    fig = px.pie(counts, values="Count", names=col, title=title,
                 hole=0.3, color=col,
                 color_discrete_map=color_map,
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(height=420)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def timeline_chart(df):
    if df.empty or "timestamp" not in df.columns:
        return None
    ds = df.dropna(subset=["timestamp"]).sort_values("timestamp").copy()
    if ds.empty:
        return None
    ds["cumulative"] = range(1, len(ds) + 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ds["timestamp"], y=ds["cumulative"],
        mode="lines+markers", name="Cumulative",
        line=dict(color="#FF4B4B", width=2),
        fill="tozeroy", fillcolor="rgba(255,75,75,0.15)"
    ))
    if "severity" in ds.columns:
        for sev, color in SEVERITY_COLORS.items():
            mask = ds["severity"] == sev
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=ds[mask]["timestamp"], y=ds[mask]["cumulative"],
                    mode="markers", name=sev,
                    marker=dict(size=10, color=color)
                ))
    fig.update_layout(title="📅 Crash Timeline", height=420,
                      xaxis_title="Timestamp", yaxis_title="Cumulative Crashes",
                      hovermode="x unified")
    return fig


def causes_bar(df):
    if df.empty or "probable_cause" not in df.columns:
        return None
    top = df["probable_cause"].dropna().value_counts().head(10).reset_index()
    top.columns = ["Cause", "Count"]
    fig = px.bar(top, x="Count", y="Cause", orientation="h",
                 title="🎯 Top 10 Probable Causes",
                 color="Count", color_continuous_scale="Reds", text="Count")
    fig.update_layout(height=480, showlegend=False)
    fig.update_traces(textposition="outside")
    return fig


def scatter_cpu_mem(df):
    if df.empty:
        return None
    cols = ["cpu_usage_percent", "memory_used_mb"]
    sd = df.dropna(subset=cols)
    if sd.empty:
        return None
    hover = [c for c in ["fault_name", "process_name", "probable_cause", "severity"] if c in sd.columns]
    fig = px.scatter(sd, x="cpu_usage_percent", y="memory_used_mb",
                     color="severity" if "severity" in sd.columns else None,
                     size="stack_depth" if "stack_depth" in sd.columns else None,
                     hover_data=hover,
                     title="💻 CPU vs Memory at Crash Time",
                     labels={"cpu_usage_percent": "CPU (%)", "memory_used_mb": "Memory (MB)"},
                     color_discrete_map=SEVERITY_COLORS)
    fig.update_layout(height=420)
    return fig


def confidence_gauge(df):
    if df.empty or "confidence_score" not in df.columns:
        return None
    avg = df["confidence_score"].dropna().mean()
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=avg,
        title={"text": "Avg Confidence Score"},
        gauge={"axis": {"range": [0, 100]},
               "bar":  {"color": "#FF4B4B"},
               "steps": [{"range": [0, 33],  "color": "lightgreen"},
                          {"range": [33, 66], "color": "orange"},
                          {"range": [66, 100],"color": "#ff6b6b"}],
               "threshold": {"line": {"color": "red", "width": 4},
                             "thickness": 0.75, "value": avg}}
    ))
    fig.update_layout(height=280)
    return fig


def hourly_dist(df):
    if df.empty or "hour" not in df.columns:
        return None
    hd = df["hour"].dropna().value_counts().sort_index().reset_index()
    hd.columns = ["hour", "count"]
    fig = px.bar(hd, x="hour", y="count",
                 title="⏰ Crashes by Hour", color="count",
                 color_continuous_scale="Reds",
                 labels={"hour": "Hour (24h)", "count": "Crashes"})
    fig.update_layout(height=280)
    return fig


def resource_bar(df):
    if df.empty or "fault_name" not in df.columns:
        return None
    g = df.groupby("fault_name")[["cpu_usage_percent", "memory_used_mb", "stack_depth"]].mean().reset_index().dropna()
    if g.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(name="CPU (%)", x=g["fault_name"], y=g["cpu_usage_percent"], marker_color="#FF6B6B"))
    fig.add_trace(go.Bar(name="Mem (MB/10)", x=g["fault_name"], y=g["memory_used_mb"] / 10, marker_color="#4ECDC4"))
    fig.update_layout(title="📊 Resource Usage by Fault Type", height=420,
                      barmode="group", xaxis_tickangle=-45)
    return fig


def heatmap_corr(df):
    if df.empty:
        return None
    cols = [c for c in ["cpu_usage_percent", "memory_used_mb", "stack_depth",
                         "thread_count", "confidence_score"] if c in df.columns]
    if len(cols) < 2:
        return None
    cm = df[cols].dropna().corr()
    if cm.empty:
        return None
    fig = go.Figure(go.Heatmap(
        z=cm.values, x=cm.columns, y=cm.columns,
        colorscale="RdBu", zmin=-1, zmax=1,
        text=cm.round(2).values, texttemplate="%{text}", textfont={"size": 10}
    ))
    fig.update_layout(title="📈 Metric Correlation Heatmap", height=420)
    return fig


def safe_slider(df, col, label):
    if col not in df.columns or df.empty:
        return None
    vals = df[col].dropna()
    if vals.empty:
        return None
    mn, mx = float(vals.min()), float(vals.max())
    if np.isnan(mn) or np.isnan(mx):
        return None
    if abs(mn - mx) < 0.001:
        mn -= 1; mx += 1
    try:
        return st.slider(label, min_value=mn, max_value=mx, value=(mn, mx))
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  DIAG CLASS / SEQUENCE / USE CASE  (text-based, rendered in a styled box)
# ─────────────────────────────────────────────────────────────────────────────

DIAG_CLASS = """
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│         <<Singleton>>            │   │      <<Interface>>               │
│       CoreDumpManager            │   │      ICrashExporter              │
├──────────────────────────────────┤   ├──────────────────────────────────┤
│ - data_: CoreDumpData            │   │ + Export(data, path): bool       │
├──────────────────────────────────┤   └───────────────┬──────────────────┘
│ + Instance(): CoreDumpManager&   │                   │ implements
│ + Store(stack, file, line, ...): │      ┌────────────┴────────────┐
│ + IsSaved(): bool                │      │                         │
│ + Get(): CoreDumpData*           │  ┌───┴──────────┐  ┌──────────┴──────┐
│ + Reset(): void                  │  │JsonCrashExp. │  │CsvCrashExporter │
│ + ExportTo(format, path): bool   │  ├──────────────┤  ├─────────────────┤
│ + Analyze(): void                │  │+Export(...)  │  │+Export(...)     │
└──────────────┬───────────────────┘  └──────────────┘  └─────────────────┘
               │ uses                      ▲
               ▼                           │ creates
┌─────────────────────────┐   ┌────────────────────────────┐
│      CoreDumpData       │   │   CrashExporterFactory     │
├─────────────────────────┤   ├────────────────────────────┤
│ key, not_key, is_valid  │   │ + Create(format): IExporter│
│ type: FaultType         │   └────────────────────────────┘
│ timestamp, date_time    │
│ file_name, line_number  │   ┌──────────────────────────┐
│ process_id, thread_id   │   │     SystemMetrics         │
│ call_stack[32]          │   ├──────────────────────────┤
│ stack_depth             │   │ cpu_usage_percent: double │
│ metrics: SystemMetrics  │   │ memory_used_kb: uint64    │
│ analysis: CrashAnalysis │   │ memory_total_kb: uint64   │
└─────────────────────────┘   │ thread_count: int         │
                               │ process_name: char[]      │
┌──────────────────────────┐   └──────────────────────────┘
│     CrashAnalysis        │
├──────────────────────────┤   ┌──────────────────────────┐
│ probable_cause: char[]   │   │     CrashSimulator       │
│ severity: char[]         │   ├──────────────────────────┤
│ recommendation: char[]   │   │ + PrintMenu(): void      │
│ confidence_score: int    │   │ + Run(index): void       │
└──────────────────────────┘   │ + RunRandom(): void      │
                               │ - sim_null_deref()       │
enum FaultType {               │ - sim_div_by_zero_int()  │
  HardwareException  = 1       │ - sim_double_free()      │
  SegmentationFault  = 2       │ - sim_heap_corruption()  │
  AbortSignal        = 3       │ - sim_stack_overflow()   │
  IllegalInstruction = 4       │ - sim_deep_chain()       │
  BusError           = 5       │ ...14 scenarios total    │
  TraceTrap          = 6       └──────────────────────────┘
  BadSystemCall      = 7
  StackOverflow      = 8
  HeapCorruption     = 9
  DoubleFree         = 10
  Unknown            = 0xFF
}
"""

SEQ_DIAGRAM = """
CrashSimulator      OS Kernel        SignalHandler      CoreDumpManager       CsvCrashExporter     Dashboard
     │                  │                 │                    │                      │                 │
     │──sim_null_deref()│                 │                    │                      │                 │
     │    (SIGSEGV)──▶  │                 │                    │                      │                 │
     │                  │──SIGSEGV──────▶ │                    │                      │                 │
     │                  │                 │──Store(file,line,  │                      │                 │
     │                  │                 │    type=SIGSEGV)──▶│                      │                 │
     │                  │                 │                    │──CaptureSystemMetrics│                 │
     │                  │                 │                    │──CaptureCallStack()  │                 │
     │                  │                 │                    │──Analyze()           │                 │
     │                  │                 │                    │  (heuristic rules)   │                 │
     │                  │                 │──ExportTo(CSV)────▶│                      │                 │
     │                  │                 │                    │──Create(CSV)────────▶│                 │
     │                  │                 │                    │                      │──fopen(append)  │
     │                  │                 │                    │                      │──fprintf(row)   │
     │                  │                 │                    │                      │──fclose()       │
     │                  │                 │◀───────────────────│ (true / false)       │                 │
     │                  │                 │──std::exit(1)      │                      │                 │
     │                  │                 │                    │                      │                 │
     │ (next run / dashboard refresh)     │                    │                      │                 │
     │                                    │                    │                      │──load_csv()────▶│
     │                                    │                    │                      │                 │──pandas parse
     │                                    │                    │                      │                 │──st.plotly_chart
"""

USE_CASE_TEXT = """
╔══════════════════════════════════════════════════════════╗
║            SYSTEM USE CASE OVERVIEW                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Actors:                                                 ║
║    👤 Developer  – runs simulator, reads dashboard       ║
║    ⚙️  OS Kernel  – delivers signals to signal handlers  ║
║    🖥️  Embedded   – the target application (C++)        ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  UC-01  Simulate a Crash                                 ║
║    Actor  : Developer                                    ║
║    Pre    : CrashSimulator built; ulimit -c unlimited    ║
║    Flow   : Developer selects scenario →                 ║
║             Simulator triggers fault →                   ║
║             Kernel sends signal →                        ║
║             SignalHandler captures snapshot →            ║
║             CoreDumpManager exports CSV/JSON             ║
║                                                          ║
║  UC-02  Analyze a Crash                                  ║
║    Actor  : Developer / CrashAnalyzer                    ║
║    Pre    : crash_dump.csv present in /tmp               ║
║    Flow   : Analyzer starts → reads CoreDumpData →       ║
║             Analyze() applies heuristic rules →          ║
║             Prints severity + recommendation →           ║
║             Exports enriched CSV row                     ║
║                                                          ║
║  UC-03  View Dashboard                                   ║
║    Actor  : Developer                                    ║
║    Pre    : crash_dump.csv exists; streamlit installed   ║
║    Flow   : Developer runs "streamlit run cv_dashboard.py"
║             → Dashboard loads & parses CSV →             ║
║             Filters applied in sidebar →                 ║
║             Charts render: pie, timeline, scatter,       ║
║             heatmap, resource bars, gauge                ║
║                                                          ║
║  UC-04  Export Data                                      ║
║    Actor  : Developer                                    ║
║    Flow   : Dashboard → "Export CSV" button →            ║
║             Filtered DataFrame downloaded as .csv        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

ANALYZER_VS_SIM = """
┌─────────────────────────────────┬──────────────────────────────────┐
│        CRASH ANALYZER           │        CRASH SIMULATOR           │
├─────────────────────────────────┼──────────────────────────────────┤
│ Purpose: DETECT & DIAGNOSE      │ Purpose: GENERATE crash events   │
│          real crash events      │          on demand for testing   │
├─────────────────────────────────┼──────────────────────────────────┤
│ Trigger: OS signal received     │ Trigger: Developer command       │
│          from the target app    │          (menu, CLI, random)     │
├─────────────────────────────────┼──────────────────────────────────┤
│ Input:   CoreDumpData from      │ Input:   Scenario index          │
│          previous run           │          (1–14)                  │
├─────────────────────────────────┼──────────────────────────────────┤
│ Output:  JSON + CSV crash       │ Output:  Actual crash → signal   │
│          report files           │          handler → CSV/JSON      │
├─────────────────────────────────┼──────────────────────────────────┤
│ Heuristic engine: Analyze()     │ No analysis – pure fault gen     │
│ Severity, cause, confidence     │ Relies on Analyzer for diag      │
├─────────────────────────────────┼──────────────────────────────────┤
│ Lifecycle: runs on startup,     │ Lifecycle: run separately,       │
│ checks for stale dump, exports, │ each invocation creates one      │
│ then resets and monitors        │ crash event                      │
├─────────────────────────────────┼──────────────────────────────────┤
│ C++ class: CoreDumpManager      │ C++ class: CrashSimulator        │
│            (Singleton)          │            (14 scenarios)        │
└─────────────────────────────────┴──────────────────────────────────┘
"""


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    auto_sync_csv_to_db()  
    st.title("🔍 Crash Investigator Dashboard")
    st.markdown("*Embedded Crash Analysis & Visualization – ACTIA PFE 2026*")
    st.markdown("---")

    # ── Quick Stats Section ──────────────────────────────────────────────────
    st.markdown("## 📊 Quick Stats")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            db = st.session_state.get('db')
            if db:
                stats = db.get_stats()
                st.metric("📊 Total Crashes", stats.get('total', 0))
            else:
                st.metric("📊 Total Crashes", 0)
        except:
            st.metric("📊 Total Crashes", 0)

    with col2:
        st.metric("📁 CSV File", "Found" if CSV_PATH.exists() else "Not Found")

    with col3:
        db = st.session_state.get('db')
        st.metric("💾 Database", "Connected" if db else "Not Connected")

    st.markdown("---")






    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_dash, tab_csv, tab_analyzer, tab_sim, tab_diag = st.tabs([
        "📊 Dashboard",
        "📂 CSV Files",
        "🧠 Crash Analyzer",
        "💥 Crash Simulator",
        "📐 Diagrams & Architecture",
    ])

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB 1 – DASHBOARD
    # ═════════════════════════════════════════════════════════════════════════
    with tab_dash:
        with st.spinner("Loading crash data..."):
            df_raw = load_data()

        if df_raw.empty:
            st.error("❌ No data available. Add crash_dump.csv next to this script.")
            with st.expander("📋 Expected CSV format"):
                st.code("timestamp,unix_timestamp,fault_type,file,line,function,"
                        "process_id,thread_id,stack_depth,cpu_usage_percent,"
                        "memory_used_kb,memory_total_kb,thread_count,process_name,"
                        "probable_cause,severity,recommendation,confidence_score")
            return

        st.success(f"✅ {len(df_raw)} crash records loaded.")
        df = df_raw.copy()

        # ── Sidebar filters ────────────────────────────────────────────────
        with st.sidebar:
            st.markdown("## 🎛️ Filters")
            st.markdown("---")

            if "date" in df.columns:
                dates = sorted(df["date"].dropna().unique(), reverse=True)
                sel_dates = st.multiselect("📅 Date", dates,
                                           default=dates[:7] if len(dates) > 7 else dates)
                if sel_dates:
                    df = df[df["date"].isin(sel_dates)]

            if "severity" in df.columns:
                sevs = sorted(df["severity"].dropna().unique())
                sel_sev = st.multiselect("⚠️ Severity", sevs, default=sevs)
                if sel_sev:
                    df = df[df["severity"].isin(sel_sev)]

            if "fault_name" in df.columns:
                faults = sorted(df["fault_name"].dropna().unique())
                sel_faults = st.multiselect("🎯 Fault Type", faults, default=faults)
                if sel_faults:
                    df = df[df["fault_name"].isin(sel_faults)]

            if "process_name" in df.columns:
                procs = sorted(df["process_name"].dropna().unique())
                sel_procs = st.multiselect("🔄 Process", procs, default=procs)
                if sel_procs:
                    df = df[df["process_name"].isin(sel_procs)]

            cpu_r = safe_slider(df, "cpu_usage_percent", "💻 CPU (%)")
            if cpu_r:
                df = df[df["cpu_usage_percent"].between(*cpu_r)]

            mem_r = safe_slider(df, "memory_used_mb", "🧠 Memory (MB)")
            if mem_r:
                df = df[df["memory_used_mb"].between(*mem_r)]

            st.markdown("---")
            st.caption(f"📊 {len(df)} crashes shown")

        if df.empty:
            st.warning("⚠️ No crashes match filters.")
            return

        # ── KPI row ────────────────────────────────────────────────────────
        st.markdown("## 📊 Overview")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📈 Total Crashes", len(df))
        with c2:
            crit = df[df.get("severity", pd.Series(dtype=str)) == "CRITICAL"].shape[0] if "severity" in df.columns else 0
            st.metric("🔥 Critical", crit, f"{crit/len(df)*100:.1f}%" if len(df) else "")
        with c3:
            avg_cpu = df["cpu_usage_percent"].dropna().mean() if "cpu_usage_percent" in df.columns else float("nan")
            st.metric("💻 Avg CPU", f"{avg_cpu:.1f}%" if not np.isnan(avg_cpu) else "N/A")
        with c4:
            avg_mem = df["memory_used_mb"].dropna().mean() if "memory_used_mb" in df.columns else float("nan")
            st.metric("🧠 Avg Memory", f"{avg_mem:.0f} MB" if not np.isnan(avg_mem) else "N/A")

        st.markdown("---")

        # ── Pies ───────────────────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            fig = pie_chart(df, "severity", "📊 Severity Distribution")
            if fig: st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = pie_chart(df, "fault_name", "🎯 Fault Types")
            if fig: st.plotly_chart(fig, use_container_width=True)

        # ── Timeline ───────────────────────────────────────────────────────
        st.markdown("---")
        fig = timeline_chart(df)
        if fig: st.plotly_chart(fig, use_container_width=True)

        # ── Causes bar ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 🎯 Probable Causes")
        fig = causes_bar(df)
        if fig: st.plotly_chart(fig, use_container_width=True)

        # ── Advanced analytics ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📈 Advanced Analytics")
        c1, c2 = st.columns(2)
        with c1:
            fig = scatter_cpu_mem(df)
            if fig: st.plotly_chart(fig, use_container_width=True)
        with c2:
            cc1, cc2 = st.columns(2)
            with cc1:
                fig = confidence_gauge(df)
                if fig: st.plotly_chart(fig, use_container_width=True)
            with cc2:
                fig = hourly_dist(df)
                if fig: st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig = resource_bar(df)
            if fig: st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = heatmap_corr(df)
            if fig: st.plotly_chart(fig, use_container_width=True)

        # ── Detail table ───────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📋 Crash History")
        disp = [c for c in ["timestamp", "fault_name", "severity", "probable_cause",
                             "cpu_usage_percent", "memory_used_mb", "stack_depth",
                             "thread_count", "process_name", "confidence_score"]
                if c in df.columns]
        if disp:
            display_df = df[disp].rename(columns={
                "timestamp": "Date/Time", "fault_name": "Fault",
                "severity": "Severity", "probable_cause": "Cause",
                "cpu_usage_percent": "CPU%", "memory_used_mb": "Mem(MB)",
                "stack_depth": "StackDepth", "thread_count": "Threads",
                "process_name": "Process", "confidence_score": "Confidence"
            })

            def style_sev(val):
                colors = {"CRITICAL": "background-color:#dc3545;color:white",
                          "HIGH":     "background-color:#fd7e14;color:white",
                          "MEDIUM":   "background-color:#ffc107;color:black",
                          "LOW":      "background-color:#28a745;color:white"}
                return colors.get(str(val).upper(), "")

            styled = display_df.style.map(style_sev, subset=["Severity"])
            st.dataframe(styled, use_container_width=True, height=460,
                         column_config={
                             "Date/Time": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
                             "CPU%": st.column_config.NumberColumn(format="%.1f%%"),
                             "Mem(MB)": st.column_config.NumberColumn(format="%.0f"),
                             "Confidence": st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100),
                         })
            csv_dl = df.to_csv(index=False, encoding="utf-8")
            st.download_button("📥 Export filtered data as CSV", csv_dl,
                               f"crashes_{datetime.now():%Y%m%d_%H%M%S}.csv",
                               "text/csv", use_container_width=True)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1: st.caption(f"📊 Updated: {datetime.now():%Y-%m-%d %H:%M:%S}")
        with c2: st.caption("🔍 Crash Investigator v3.0 – ACTIA PFE 2026")
        with c3:
            if "severity" in df.columns:
                st.caption(f"⚠️ {df[df['severity']=='CRITICAL'].shape[0]} critical crashes")

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB 2 – CSV FILES
    # ═════════════════════════════════════════════════════════════════════════
    with tab_csv:
        st.markdown("## 📂 All CSV Files in Dashboard Folder")
        st.markdown(f"*Scanning `{DASHBOARD_DIR}`*")
        st.markdown("---")

        all_csv_data = load_all_csvs()
        csv_files_on_disk = discover_csv_files()

        if not csv_files_on_disk:
            st.warning("No CSV files found in the dashboard directory.")
        else:
            # ── Summary table ────────────────────────────────────────────
            summary_rows = []
            for path in csv_files_on_disk:
                size_kb = path.stat().st_size / 1024
                df_s = all_csv_data.get(path.name, pd.DataFrame())
                rows  = len(df_s)
                cols  = len(df_s.columns) if not df_s.empty else 0
                has_ts = 'timestamp' in df_s.columns if not df_s.empty else False
                summary_rows.append({
                    "File": path.name,
                    "Size (KB)": round(size_kb, 1),
                    "Rows": rows,
                    "Columns": cols,
                    "Has Timestamp": "✅" if has_ts else "—",
                    "Status": "✅ Loaded" if rows > 0 else "⚠️ Empty / Unreadable",
                })

            st.markdown("### 📋 File Overview")
            st.dataframe(
                pd.DataFrame(summary_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Size (KB)": st.column_config.NumberColumn(format="%.1f"),
                    "Rows": st.column_config.NumberColumn(),
                },
            )

            st.markdown("---")
            st.markdown("### 🔍 Inspect a File")

            sel_file = st.selectbox(
                "Select CSV file to inspect",
                [p.name for p in csv_files_on_disk],
            )

            if sel_file:
                df_sel = all_csv_data.get(sel_file, pd.DataFrame())
                # Resolve the real path from the discovered list (file may not be in DASHBOARD_DIR)
                path_sel_matches = [p for p in csv_files_on_disk if p.name == sel_file]
                path_sel = path_sel_matches[0] if path_sel_matches else (DASHBOARD_DIR / sel_file)

                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("Rows", len(df_sel))
                with col_info2:
                    st.metric("Columns", len(df_sel.columns) if not df_sel.empty else 0)
                with col_info3:
                    size_str = f"{path_sel.stat().st_size / 1024:.1f} KB" if path_sel.exists() else "N/A"
                    st.metric("Size", size_str)

                if df_sel.empty:
                    st.warning("This file is empty or could not be parsed.")
                else:
                    # ── Column schema ────────────────────────────────────
                    with st.expander("📐 Column Schema", expanded=False):
                        schema_df = pd.DataFrame({
                            "Column": df_sel.columns,
                            "Type": [str(df_sel[c].dtype) for c in df_sel.columns],
                            "Non-Null": [df_sel[c].notna().sum() for c in df_sel.columns],
                            "Sample": [str(df_sel[c].dropna().iloc[0])
                                       if df_sel[c].notna().any() else "—"
                                       for c in df_sel.columns],
                        })
                        st.dataframe(schema_df, use_container_width=True, hide_index=True)

                    # ── Severity quick chart (if column present) ─────────
                    if 'severity' in df_sel.columns:
                        sev_counts = df_sel['severity'].dropna().value_counts().reset_index()
                        sev_counts.columns = ['Severity', 'Count']
                        fig_sev = px.bar(
                            sev_counts, x='Severity', y='Count',
                            color='Severity', color_discrete_map=SEVERITY_COLORS,
                            title=f"Severity Distribution – {sel_file}",
                        )
                        st.plotly_chart(fig_sev, use_container_width=True)

                    # ── Fault type pie (if column present) ───────────────
                    if 'fault_name' in df_sel.columns:
                        fig_fault = pie_chart(df_sel, 'fault_name', f"Fault Types – {sel_file}")
                        if fig_fault:
                            st.plotly_chart(fig_fault, use_container_width=True)

                    # ── Full data table ───────────────────────────────────
                    st.markdown("#### 📄 Data")
                    st.dataframe(df_sel, use_container_width=True, height=400)

                    # ── Download button ───────────────────────────────────
                    if path_sel.exists():
                        raw_bytes = path_sel.read_bytes()
                    else:
                        raw_bytes = df_sel.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label=f"📥 Download {sel_file}",
                        data=raw_bytes,
                        file_name=sel_file,
                        mime="text/csv",
                        use_container_width=True,
                    )

            st.markdown("---")
            st.markdown("### 🔗 Merged View (all files combined)")
            merged_all = pd.concat(all_csv_data.values(), ignore_index=True) if all_csv_data else pd.DataFrame()
            if not merged_all.empty:
                st.caption(f"{len(merged_all)} total rows from {len(all_csv_data)} file(s)")
                show_cols = [c for c in ['_source', 'timestamp', 'fault_name', 'severity',
                                          'probable_cause', 'process_name', 'confidence_score']
                             if c in merged_all.columns]
                st.dataframe(merged_all[show_cols], use_container_width=True, height=380)
                merged_csv = merged_all.to_csv(index=False)
                st.download_button(
                    "📥 Export merged CSV",
                    merged_csv,
                    f"merged_all_{datetime.now():%Y%m%d_%H%M%S}.csv",
                    "text/csv",
                    use_container_width=True,
                )

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB 3 – CRASH ANALYZER
    # ═════════════════════════════════════════════════════════════════════════
    with tab_analyzer:
        st.markdown("## 🧠 Python Crash Analyzer")
        st.markdown("*Mirrors the C++ `CoreDumpManager::Analyze()` heuristic engine*")
        st.markdown("---")

        st.markdown("### 🔬 Analyze a Single Crash")
        c1, c2 = st.columns(2)
        with c1:
            fault_sel = st.selectbox("Fault Type", options=list(FAULT_MAP.items()),
                                     format_func=lambda x: f"{x[0]} – {x[1]}")
            fault_id = fault_sel[0]
        with c2:
            cpu_val  = st.slider("CPU % at crash time", 0.0, 100.0, 45.0, 0.5)
        c3, c4 = st.columns(2)
        with c3:
            mem_used  = st.number_input("Memory used (KB)", 0, 32_000_000, 13_000_000, 100_000)
        with c4:
            mem_total = st.number_input("Memory total (KB)", 1, 32_000_000, 16_553_776, 100_000)

        if st.button("🔍 Run Analysis", use_container_width=True):
            result = python_analyze(fault_id, cpu_val, mem_used, mem_total)
            sev_color = SEVERITY_COLORS.get(result["severity"], "#666")
            st.markdown(f"""
<div style="background:#1e1e1e;padding:1.2rem;border-radius:10px;border-left:5px solid {sev_color};margin-top:1rem">
  <h4 style="color:{sev_color}">⚠️ Severity: {result['severity']}</h4>
  <p><b style="color:#aaa">Probable Cause:</b><br><span style="color:#e0e0e0">{result['probable_cause']}</span></p>
  <p><b style="color:#aaa">Recommendation:</b><br><span style="color:#80cbc4">{result['recommendation']}</span></p>
  <p><b style="color:#aaa">Confidence Score:</b> <span style="color:#fff;font-size:1.3rem"><b>{result['confidence']}%</b></span></p>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Re-analyze All Loaded Crashes")
        df_a = load_data()
        if not df_a.empty and "fault_type" in df_a.columns:
            if st.button("⚡ Re-analyze with Python Engine", use_container_width=True):
                results = []
                for _, row in df_a.iterrows():
                    ft  = int(row["fault_type"]) if pd.notna(row.get("fault_type")) else 0
                    cpu = float(row["cpu_usage_percent"]) if pd.notna(row.get("cpu_usage_percent")) else 0.0
                    mu  = float(row["memory_used_kb"])    if pd.notna(row.get("memory_used_kb"))    else 0.0
                    mt  = float(row["memory_total_kb"])   if pd.notna(row.get("memory_total_kb"))   else 1.0
                    r = python_analyze(ft, cpu, mu, mt)
                    results.append(r)
                res_df = pd.DataFrame(results)
                res_df.index = df_a["timestamp"].values if "timestamp" in df_a.columns else res_df.index
                st.dataframe(res_df, use_container_width=True, height=400)

                sev_counts = res_df["severity"].value_counts().reset_index()
                sev_counts.columns = ["Severity", "Count"]
                fig = px.bar(sev_counts, x="Severity", y="Count",
                             color="Severity", color_discrete_map=SEVERITY_COLORS,
                             title="Re-analysis Severity Distribution")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔑 Analyzer vs Simulator – Key Differences")
        st.markdown(f"```\n{ANALYZER_VS_SIM}\n```")

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB 3 – CRASH SIMULATOR
    # ═════════════════════════════════════════════════════════════════════════
    with tab_sim:
        st.markdown("## 💥 Crash Simulator")
        st.markdown("*Generates synthetic crash events and appends them to crash_dump.csv*")
        st.markdown("---")

        st.markdown("### 📋 Available Scenarios")
        for s in SIM_SCENARIOS:
            sig_color = {"SIGSEGV": "#dc3545", "SIGABRT": "#fd7e14",
                         "SIGFPE": "#ffc107",  "SIGILL":  "#6f42c1",
                         "SIGBUS": "#17a2b8"}.get(s["signal"], "#666")
            st.markdown(
                f'<div class="sim-card">'
                f'<b>#{s["id"]:02d} – {s["name"]}</b> &nbsp;&nbsp;'
                f'<span style="background:{sig_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8rem">{s["signal"]}</span>'
                f'<br><small style="color:#aaa">{s["desc"]}</small></div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("### ▶️ Trigger a Simulation")

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            scenario_names = [f"#{s['id']:02d} – {s['name']}" for s in SIM_SCENARIOS]
            sel_name = st.selectbox("Select Scenario", ["🎲 Random"] + scenario_names)
        with c2:
            proc_name = st.text_input("Process Name", value="CoreDumpApp")
        with c3:
            n_runs = st.number_input("Repeat count", 1, 50, 1)

        if st.button("💥 Simulate Crash", use_container_width=True, type="primary"):
            if sel_name == "🎲 Random":
                chosen = [random.choice(SIM_SCENARIOS) for _ in range(n_runs)]
            else:
                idx = int(sel_name.split("–")[0].strip("#").strip()) - 1
                chosen = [SIM_SCENARIOS[idx]] * n_runs

            generated = []
            for sc in chosen:
                row = simulate_crash(sc, proc_name)
                append_to_csv(row, CSV_PATH)
                generated.append(row)

            st.success(f"✅ {len(generated)} crash(es) generated and appended to `crash_dump.csv`")
            gen_df = pd.DataFrame(generated)
            st.dataframe(gen_df[["timestamp", "fault_type", "severity",
                                  "probable_cause", "cpu_usage_percent",
                                  "memory_used_mb" if "memory_used_mb" in gen_df.columns
                                  else "memory_used_kb",
                                  "confidence_score"]],
                         use_container_width=True)

            # Show analysis cards
            for row in generated:
                sev_color = SEVERITY_COLORS.get(row["severity"], "#666")
                st.markdown(f"""
<div style="background:#1e1e2e;padding:1rem;border-radius:8px;
            border-left:4px solid {sev_color};margin:0.5rem 0">
  <b style="color:{sev_color}">⚠️ {row['severity']}</b> &nbsp; | &nbsp;
  Fault: <b>{FAULT_MAP.get(row['fault_type'], '?')}</b> &nbsp; | &nbsp;
  Confidence: <b>{row['confidence_score']}%</b><br>
  <small style="color:#aaa">{row['probable_cause']}</small><br>
  <small style="color:#80cbc4">→ {row['recommendation']}</small>
</div>
""", unsafe_allow_html=True)

            st.info("🔄 Switch to the **Dashboard** tab and refresh to see the new crashes.")
            # Clear cache so next load picks up new rows
            load_csv.clear()

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB 4 – DIAGRAMS
    # ═════════════════════════════════════════════════════════════════════════
    with tab_diag:
        st.markdown("## 📐 Architecture & Diagrams")
        st.markdown("---")

        st.markdown("### 🗂️ Class Diagram")
        st.markdown(f'<div class="diag-box">{DIAG_CLASS}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔁 Sequence Diagram – Crash Capture Flow")
        st.markdown(f'<div class="diag-box">{SEQ_DIAGRAM}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 👤 Use Case Overview")
        st.markdown(f'<div class="diag-box">{USE_CASE_TEXT}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⚙️ Analyzer vs Simulator")
        st.markdown(f'<div class="diag-box">{ANALYZER_VS_SIM}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📁 Project Structure")
        st.markdown("""
```
CoreDump_PFE/
├── analyzer/                   ← C++ Crash Analyzer (collector/detector)
│   ├── inc/
│   │   ├── Options.hpp         ← Feature flags, constants, INTEGER_TYPE
│   │   ├── Platform.hpp        ← POSIX signal / PID / backtrace wrappers
│   │   ├── SystemMetrics.hpp   ← OS snapshot struct + CaptureSystemMetrics()
│   │   └── CoreDump.hpp        ← CoreDumpManager, ICrashExporter, FaultType
│   ├── src/
│   │   ├── main.cpp            ← Entry point, installs signal handlers
│   │   ├── CoreDump.cpp        ← Singleton + heuristic Analyze() + exporters
│   │   ├── SystemMetrics.cpp   ← Linux /proc implementation
│   │   └── crash_handler.cpp   ← SignalHandler + HandlePreviousCrash()
│   └── CMakeLists.txt
│
├── simulator/                  ← C++ Crash Simulator (fault generator)
│   ├── inc/
│   │   ├── Options.hpp         ← (shared copy)
│   │   ├── Platform.hpp        ← (shared copy)
│   │   └── CrashSim.hpp        ← CrashSimulator class (14 scenarios)
│   ├── src/
│   │   ├── main.cpp            ← Interactive menu + CLI interface
│   │   └── CrashSim.cpp        ← 14 fault generator implementations
│   ├── test/
│   │   └── test_crash.cpp      ← Regression test (signal capture validation)
│   └── CMakeLists.txt
│
├── pc_tools/                   ← Python tools
│   ├── cv_dashboard.py         ← THIS FILE – Streamlit dashboard
│   └── crash_dump.csv          ← Output from C++ analyzer / simulator
│
└── docs/
    └── PFE-2026_Code-review.docx
```
""")


if __name__ == "__main__":
    main()