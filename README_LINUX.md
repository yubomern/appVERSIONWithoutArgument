# Crash Simulator - Linux Build & Test Guide

Complete guide for building, testing, and running the Crash Simulator project on Linux (Ubuntu/Debian).

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Building](#building)
4. [Running Tests](#running-tests)
5. [Core Dump Configuration](#core-dump-configuration)
6. [Viewing Results](#viewing-results)
7. [Dashboard Setup](#dashboard-setup)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Specifications

- **OS**: Ubuntu 20.04 LTS, Debian 11, or equivalent
- **RAM**: 2GB minimum
- **Disk Space**: 500MB
- **Compiler**: GCC 9 or higher
- **CMake**: 3.16 or higher
- **Python**: 3.8 or higher

### Supported Distributions

- Ubuntu 20.04 LTS ✅
- Ubuntu 22.04 LTS ✅
- Debian 11 (Bullseye) ✅
- Debian 12 (Bookworm) ✅
- Fedora 38+ ✅
- CentOS 8+ ✅

---

## Installation

### Step 1: Update Package Manager

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install Build Tools

```bash
sudo apt-get install -y \
    build-essential \
    cmake \
    g++ \
    git \
    python3 \
    python3-pip \
    python3-venv
```

**Verify installation:**

```bash
gcc --version
cmake --version
python3 --version
```

### Step 3: Install Python Dependencies

```bash
pip3 install --upgrade pip
pip3 install pandas streamlit plotly numpy
```

**Optional**: Create a virtual environment for isolated dependencies

```bash
python3 -m venv crash_sim_env
source crash_sim_env/bin/activate
pip install pandas streamlit plotly
```

### Step 4: Clone/Download Project

```bash
cd ~/workspace
git clone <repository-url> appopCPP-main
cd appopCPP-main
```

Or extract the provided archive:

```bash
tar -xzf appopCPP-main.tar.gz
cd appopCPP-main
```

---

## Building

### Quick Start

```bash
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build . --config Debug
```

**Expected output:**
```
[ 10%] Building CXX object CMakeFiles/coredump_core.lib...
[ 20%] Linking CXX static library Debug/coredump_core.lib
[ 30%] Building CXX object CMakeFiles/CoreDumpApp.dir/...
[ 40%] Linking CXX executable Debug/CoreDumpApp
[ 50%] Building CXX object CMakeFiles/test_crash_simulator.dir/...
[ 60%] Linking CXX executable Debug/test_crash_simulator
[ 70%] Building CXX object CMakeFiles/test_crash_analyzer.dir/...
[ 80%] Linking CXX executable Debug/test_crash_analyzer
[ 90%] Building CXX object CMakeFiles/test_artificial_crash.dir/...
[100%] Linking CXX executable Debug/test_artificial_crash

Built target coredump_core
Built target CoreDumpApp
Built target test_crash_simulator
Built target test_crash_analyzer
Built target test_artificial_crash
```

### Build Targets

The build produces 5 main targets:

| Target | Binary | Purpose |
|--------|--------|---------|
| `CoreDumpApp` | `./build/Debug/CoreDumpApp` | Main application with embedded test mode |
| `test_crash_simulator` | `./build/Debug/test_crash_simulator` | Safe-mode crash simulator |
| `test_crash_analyzer` | `./build/Debug/test_crash_analyzer` | Crash test analyzer with CSV export |
| `test_artificial_crash` | `./build/Debug/test_artificial_crash` | Synthetic crash generator |
| `coredump_core` | (library) | Shared crash dump library |

### Release Build (Optional)

For optimized performance:

```bash
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --config Release
```

### Rebuild (Clean Build)

```bash
rm -rf build
mkdir build
cd build
cmake ..
cmake --build .
```

---

## Running Tests

### Test 1: Crash Simulator (Safe Mode)

Simulates crashes without actual crashes:

```bash
./build/Debug/test_crash_simulator --test safe
```

**Output:**
```
▶ Running C++ crash simulator in safe mode
[0/5] Executing crash test type 0...
[Test 0] Abort Signal - CSV appended
[1/5] Executing crash test type 1...
[Test 1] Null Pointer Dereference - CSV appended
...
```

### Test 2: Crash Analyzer

Runs 6 automated crash tests and exports CSV:

```bash
./build/Debug/test_crash_analyzer
```

**Output:**
```
╔════════════════════════════════════════════════════════════════════╗
║  Crash Simulator - Test Suite with CSV Export                      ║
║  Safe Mode: All tests simulated (no actual crashes)                 ║
╚════════════════════════════════════════════════════════════════════╝

======================================================================
  CRASH TEST SUITE - SAFE MODE (No actual crashes)
======================================================================

[0/5] Test: Abort Signal
  Description: Simulates std::abort() - abnormal program termination
  Severity: HIGH
  Result: ✅ SIMULATED (No crash occurred)

[1/5] Test: Null Pointer Dereference
  Description: Attempts to dereference a nullptr - causes SIGSEGV
  Severity: CRITICAL
  Result: ✅ SIMULATED (No crash occurred)
...

💾 Saving results to CSV...
  Dashboard path: /home/user/appopCPP-main/dashbaord
  ✅ Results saved to: /home/user/appopCPP-main/dashbaord/test_crash_results.csv
```

### Test 3: Artificial Crash Export

Generates synthetic crash data:

```bash
./build/Debug/test_artificial_crash
```

**Output:**
```
Artificial crash test exported to /home/user/appopCPP-main/dashbaord/artificial_test_results.csv
```

### Run All Tests with CTest

Execute all 3 tests via CTest:

```bash
cd build
ctest -C Debug --output-on-failure
```

**Expected output:**
```
    Start 1: cpp_test_crash_simulator
1/3 Test #1: cpp_test_crash_simulator ............ Passed    2.83 sec
    Start 2: cpp_test_crash_analyzer
2/3 Test #2: cpp_test_crash_analyzer ............ Passed    1.66 sec
    Start 3: cpp_test_artificial_export
3/3 Test #3: cpp_test_artificial_export ........ Passed    1.61 sec

100% tests passed, 0 tests failed out of 3
Total Test time (real) =   6.32 sec
```

### Run Dashboard Test Aggregator

Consolidates all C++ CSV outputs for dashboard:

```bash
python3 dashbaord/run_all_tests.py
```

**Output:**
```
Crash Test Runner
Simulator: ./build/Debug/test_crash_simulator
Analyzer: ./build/Debug/test_crash_analyzer
Artificial test: ./build/Debug/test_artificial_crash

▶ Running C++ crash simulator in safe mode
[Test 0] Abort Signal - CSV appended
[Test 1] Null Pointer Dereference - CSV appended
...

▶ Generating C++ analyzer CSV export
▶ Generating artificial crash export

Loaded 6 rows from crash_dump.csv
Loaded 6 rows from test_crash_results.csv
Loaded 1 rows from artificial_test_results.csv
Saved 13 consolidated records to ./dashbaord/cpp_test_crash_results.csv
```

---

## Core Dump Configuration

### Enable Core Dumps

To allow the application to generate core dumps:

```bash
# Allow unlimited core dumps in current session
ulimit -c unlimited

# Verify configuration
ulimit -a | grep core
```

**Output:**
```
core file size          (blocks, -c) unlimited
```

### Make Core Dumps Permanent (Optional)

Add to `~/.bashrc` or `~/.profile`:

```bash
# Enable core dumps
ulimit -c unlimited
```

Then reload:

```bash
source ~/.bashrc
```

### System-Wide Core Dump Configuration

For system administrators to configure globally:

```bash
# Edit sysctl configuration
sudo nano /etc/sysctl.conf

# Add these lines:
kernel.core_pattern=/var/crash/core.%u.%p.%s.%e.%t
kernel.core_uses_pid=1

# Apply changes
sudo sysctl -p
```

### Locate Core Dumps

Core dumps are typically saved to:

```bash
# Current directory
ls -la core*

# Check system crash directory
ls -la /var/crash/

# Check kernel core pattern
cat /proc/sys/kernel/core_pattern
```

---

## Viewing Results

### CSV Output Files

Test results are saved to the `dashbaord/` directory:

```bash
ls -la dashbaord/*.csv
```

**Files:**
- `crash_dump.csv` – Consolidated crash results (dashboard input)
- `test_crash_results.csv` – Analyzer test output
- `artificial_test_results.csv` – Artificial crash export
- `cpp_test_crash_results.csv` – Consolidated C++ test results

### View Results in Terminal

```bash
# Display first 10 rows
head -20 dashbaord/crash_dump.csv

# Count total records
wc -l dashbaord/crash_dump.csv

# View with column headers
column -t -s',' dashbaord/crash_dump.csv | head -20
```

### Load Results in Python

```python
import pandas as pd

# Load crash data
df = pd.read_csv('dashbaord/crash_dump.csv')

# Display summary
print(f"Total crashes: {len(df)}")
print(f"\nCrash types:\n{df['fault_type'].value_counts()}")
print(f"\nSeverities:\n{df['severity'].value_counts()}")

# Display sample records
print(df[['timestamp', 'test_name', 'severity', 'process_id']].head())

# Filter by severity
critical = df[df['severity'] == 'CRITICAL']
print(f"\nCritical issues: {len(critical)}")
```

**Output:**
```
Total crashes: 13

Crash types:
0    1
1    1
2    1
3    1
9001    1
Name: fault_type, dtype: int64

Severities:
HIGH       4
CRITICAL   6
Name: severity, dtype: int64

   timestamp test_name     severity process_id
0  2026-04-05 Abort Signal HIGH 1234
1  2026-04-05 Null Pointer Dereference CRITICAL 1234
2  2026-04-05 Stack Overflow CRITICAL 1234
3  2026-04-05 Invalid Memory Access CRITICAL 1234

Critical issues: 6
```

---

## Dashboard Setup

### Install Streamlit

```bash
pip3 install streamlit
```

### Run Dashboard

```bash
cd /path/to/appopCPP-main
streamlit run dashbaord/dashbaord.py
```

**Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501

  For better performance, install pyarrow: pip install pyarrow
```

### Access Dashboard

Open browser and navigate to: `http://localhost:8501`

**Features:**
- Real-time crash visualization
- Crash timeline and heatmaps
- Fault type distribution
- System metrics at crash time
- Searchable crash logs

### Stop Dashboard

Press `Ctrl+C` in the terminal:

```bash
^C
Shutting down...
```

---

## Troubleshooting

### Build Issues

#### CMake Not Found

```bash
sudo apt-get install cmake
cmake --version
```

#### GCC Compilation Errors

```bash
# Update GCC
sudo apt-get install g++
g++ --version

# If using Ubuntu 20.04, consider upgrading to GCC 10+
sudo apt-get install g++-10
export CXX=/usr/bin/g++-10
```

#### Missing Dependencies

```bash
# Reinstall build tools
sudo apt-get install --reinstall build-essential

# Check for broken dependencies
sudo apt --fix-broken install
```

### Test Failures

#### Tests Timeout

Increase timeout in terminal:

```bash
ctest -C Debug --output-on-failure --timeout 120
```

#### Python Module Not Found

```bash
pip3 install --upgrade pandas streamlit plotly

# Or use virtual environment
python3 -m venv env
source env/bin/activate
pip install pandas streamlit plotly
```

#### CSV Export Fails

```bash
# Check directory permissions
ls -ld dashbaord/
chmod 755 dashbaord/

# Ensure write permissions
touch dashbaord/test.txt
rm dashbaord/test.txt
```

### Core Dump Issues

#### Core Dumps Not Generated

```bash
# Check if core dumps are enabled
ulimit -c

# Enable unlimited core dumps
ulimit -c unlimited

# Verify
ulimit -c
```

#### Cannot Find Core Files

```bash
# Search for core files
find ~ -name "core*" 2>/dev/null

# Check system crash directory
sudo ls -la /var/crash/

# Check current directory
ls -la core*
```

### Performance Issues

#### Slow Build

```bash
# Use parallel build (replace N with number of CPU cores)
cmake --build . --config Debug -- -j N

# Example: 4 cores
cmake --build . --config Debug -- -j 4
```

#### High Memory Usage

Build with limited parallelism:

```bash
cmake --build . --config Debug -- -j 2
```

---

## Quick Reference

### Common Commands

```bash
# Build
cd ~/appopCPP-main
mkdir -p build && cd build
cmake .. && cmake --build .

# Test
ctest --output-on-failure

# View results
python3 -c "import pandas as pd; print(pd.read_csv('../dashbaord/crash_dump.csv'))"

# Run dashboard
streamlit run ../dashbaord/dashbaord.py
```

### Environment Setup Script

Save as `setup_linux.sh`:

```bash
#!/bin/bash
set -e

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y build-essential cmake g++ python3-pip

echo "Installing Python packages..."
pip3 install pandas streamlit plotly

echo "Building project..."
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build .

echo "✅ Setup complete!"
echo "Run tests: ctest --output-on-failure"
echo "Run dashboard: streamlit run ../dashbaord/dashbaord.py"
```

Make executable:

```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

---

## Support & Additional Resources

For issues or questions:

1. Check [main README](./Readme.md) for general information
2. Review [CMakeLists.txt](./CMakeLists.txt) for build configuration
3. Check test source files in [test/](./test/) directory
4. Consult [dashbaord/README](./dashbaord/) for dashboard-specific issues

---

**Last Updated**: April 6, 2026  
**Tested On**: Ubuntu 22.04 LTS with GCC 11, CMake 3.22, Python 3.10
