/*
 * test_crash_csv_analyzer.cpp
 * Multi-threaded crash CSV analyzer (no CLI arguments)
 *
 * Build:
 *   g++ -std=c++17 -O2 -pthread test_crash_csv_analyzer.cpp -o crash_analyzer
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <iomanip>
#include <atomic>
#include <thread>
#include <mutex>
#include <queue>
#include <condition_variable>
#include <functional>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <sys/stat.h>
#endif

#define CSV_PATH "../crash_simulator/build/crash_report.csv"
#define EXPORT_PATH "analysis_report.csv"
// ─────────────────────────────────────────────────────────────────────────────
// Configuration (NO ARGUMENTS)
// ─────────────────────────────────────────────────────────────────────────────

static constexpr const char* CSV_PATHV1 =
    "../crash_simulator/build/crash_report.csv";
static constexpr const char* EXPORT_PATHV1 =
    "analysis_report.csv";

// ─────────────────────────────────────────────────────────────────────────────
// Thread Pool
// ─────────────────────────────────────────────────────────────────────────────

class ThreadPool {
public:
    explicit ThreadPool(size_t threads) : stop(false) {
        for (size_t i = 0; i < threads; ++i) {
            workers.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(mutex);
                        cv.wait(lock, [this] {
                            return stop || !tasks.empty();
                        });
                        if (stop && tasks.empty())
                            return;
                        task = std::move(tasks.front());
                        tasks.pop();
                    }
                    task();
                }
            });
        }
    }

    template <class F>
    void enqueue(F&& task) {
        {
            std::lock_guard<std::mutex> lock(mutex);
            tasks.emplace(std::forward<F>(task));
        }
        cv.notify_one();
    }

    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mutex);
            stop = true;
        }
        cv.notify_all();
        for (auto& t : workers)
            t.join();
    }

private:
    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    std::mutex mutex;
    std::condition_variable cv;
    bool stop;
};

// ─────────────────────────────────────────────────────────────────────────────
// Crash Data Structure
// ─────────────────────────────────────────────────────────────────────────────

struct CrashData {
    std::string timestamp;
    long unix_timestamp;
    int category;
    std::string category_name;
    unsigned int seed;
    std::string description;
    int call_chain_depth;
    uint32_t exception_code;
    int intensity;
    int recursion_depth;
    size_t memory_size;
    bool random_mode;
    bool generate_minidump;
};

// ─────────────────────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────────────────────

static std::mutex g_printMutex;

bool fileExists(const std::string& path) {
#ifdef _WIN32
    return GetFileAttributesA(path.c_str()) != INVALID_FILE_ATTRIBUTES;
#else
    struct stat buffer;
    return stat(path.c_str(), &buffer) == 0;
#endif
}

std::vector<std::string> parseCSVLine(const std::string& line) {
    std::vector<std::string> cells;
    bool inQuotes = false;
    std::string cell;

    for (char c : line) {
        if (c == '"') {
            inQuotes = !inQuotes;
        } else if (c == ',' && !inQuotes) {
            cells.push_back(cell);
            cell.clear();
        } else {
            cell += c;
        }
    }
    cells.push_back(cell);
    return cells;
}

// ─────────────────────────────────────────────────────────────────────────────
// CSV Reader
// ─────────────────────────────────────────────────────────────────────────────

std::vector<CrashData> readCrashCSV(const std::string& path) {
    std::vector<CrashData> crashes;
    std::ifstream file(path);

    if (!file.is_open()) {
        std::cerr << "ERROR: Failed to open: " << path << '\n';
        return crashes;
    }

    std::string line;
    int lineNum = 0;

    while (std::getline(file, line)) {
        ++lineNum;
        if (lineNum == 1 || line.empty()) continue;

        auto cells = parseCSVLine(line);
        if (cells.size() < 13) continue;

        try {
            CrashData c;
            c.timestamp = cells[0];
            c.unix_timestamp = std::stol(cells[1]);
            c.category = std::stoi(cells[2]);
            c.category_name = cells[3];
            c.seed = std::stoul(cells[4]);
            c.description = cells[5];
            c.call_chain_depth = std::stoi(cells[6]);
            c.exception_code = std::stoul(cells[7]);
            c.intensity = std::stoi(cells[8]);
            c.recursion_depth = std::stoi(cells[9]);
            c.memory_size = std::stoull(cells[10]);
            c.random_mode = cells[11] == "true";
            c.generate_minidump = cells[12] == "true";
            crashes.push_back(c);
        } catch (...) {}
    }

    return crashes;
}

// ─────────────────────────────────────────────────────────────────────────────
// Analysis Functions (unchanged logic)
// ─────────────────────────────────────────────────────────────────────────────

void printGeneralStats(const std::vector<CrashData>& crashes) {
    std::lock_guard<std::mutex> lock(g_printMutex);
    int minI = crashes[0].intensity, maxI = crashes[0].intensity;
    int totalI = 0;

    for (const auto& c : crashes) {
        minI = std::min(minI, c.intensity);
        maxI = std::max(maxI, c.intensity);
        totalI += c.intensity;
    }

    std::cout << "\n[General Stats]\n";
    std::cout << "Crashes: " << crashes.size() << '\n';
    std::cout << "Intensity min/max/avg: "
              << minI << "/" << maxI << "/"
              << (double)totalI / crashes.size() << '\n';
}

void printCategoryDistribution(const std::vector<CrashData>& crashes) {
    std::lock_guard<std::mutex> lock(g_printMutex);
    std::map<std::string, int> counts;
    for (auto& c : crashes) counts[c.category_name]++;

    std::cout << "\n[Categories]\n";
    for (auto& [name, count] : counts)
        std::cout << name << ": " << count << '\n';
}

void printSeverityAnalysis(const std::vector<CrashData>& crashes) {
    std::lock_guard<std::mutex> lock(g_printMutex);
    std::map<int, int> sev;
    for (auto& c : crashes)
        sev[c.intensity]++;

    std::cout << "\n[Severity]\n";
    for (auto& [i, c] : sev)
        std::cout << "Level " << i << ": " << c << '\n';
}

void printTimelineAnalysis(const std::vector<CrashData>& crashes) {
    std::lock_guard<std::mutex> lock(g_printMutex);
    std::cout << "\n[Timeline]\n";
    std::cout << "First: " << crashes.front().timestamp << '\n';
    std::cout << "Last : " << crashes.back().timestamp << '\n';
}

void printTopCrashes(const std::vector<CrashData>& crashes) {
    std::lock_guard<std::mutex> lock(g_printMutex);
    std::map<std::string, int> freq;
    for (auto& c : crashes)
        freq[c.category_name]++;

    std::cout << "\n[Top Crashes]\n";
    for (auto& [name, count] : freq)
        if (count > 1)
            std::cout << name << " (" << count << ")\n";
}

void exportAnalysisToCSV(const std::vector<CrashData>& crashes) {
    std::ofstream out(EXPORT_PATH);
    std::map<std::string, int> total;

    for (auto& c : crashes)
        total[c.category_name]++;

    out << "category,count\n";
    for (auto& [k, v] : total)
        out << "\"" << k << "\"," << v << "\n";

    std::cout << "Saved: " << EXPORT_PATH << '\n';
}

// ─────────────────────────────────────────────────────────────────────────────
// Parallel Runner
// ─────────────────────────────────────────────────────────────────────────────

void runAnalysesParallel(const std::vector<CrashData>& crashes) {
    ThreadPool pool(std::thread::hardware_concurrency());
    std::atomic<int> finished{0};

    pool.enqueue([&]{ printGeneralStats(crashes); ++finished; });
    pool.enqueue([&]{ printCategoryDistribution(crashes); ++finished; });
    pool.enqueue([&]{ printSeverityAnalysis(crashes); ++finished; });
    pool.enqueue([&]{ printTimelineAnalysis(crashes); ++finished; });
    pool.enqueue([&]{ printTopCrashes(crashes); ++finished; });

    while (finished.load() < 5)
        std::this_thread::yield();
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "Crash CSV Analyzer (Multi-threaded)\n";

    if (!fileExists(CSV_PATH)) {
        std::cerr << "ERROR: Missing CSV: " << CSV_PATH << '\n';
        return 1;
    }

    auto crashes = readCrashCSV(CSV_PATH);
    if (crashes.empty()) {
        std::cerr << "WARNING: No data\n";
        return 0;
    }

    runAnalysesParallel(crashes);
    exportAnalysisToCSV(crashes);

    std::cout << "\nDone\n";
    return 0;
}