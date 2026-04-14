#include "Simulator.hpp"
#include <iostream>
#include <string>
#include <cstring>
#include <cstdlib>


#include <thread> // For sleep and threading
#include <vector> // For std::vector

#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#endif

int main(int argc, char* argv[]) {
    using namespace CrashSimulator;
    
    std::cout << "\n";
    std::cout << "╔══════════════════════════════════════════╗\n";
    std::cout << "║     Windows Crash Simulator v1.0         ║\n";
    std::cout << "║     Embedded Systems Fault Generator     ║\n";
    std::cout << "╚══════════════════════════════════════════╝\n\n";
    std::cout << "Running all crash tests in parallel threads...\n\n";
    
    std::vector<std::thread> threads;
    unsigned int base_seed = std::random_device{}(); // 0 -500
    std::mt19937 rng(base_seed); // rng range  % 500
    for (int i = 0; i < static_cast<int>(CrashCategory::COUNT); ++i) {
        threads.emplace_back([i, base_seed, rng]() {
            CrashCategory cat = static_cast<CrashCategory>(i);
            Simulator simulator(base_seed + i);
            simulator.setCrashCategory(cat);
            simulator.setIntensity(5);
            simulator.enableLogging(true);
            simulator.setGenerateMinidump(false); // Disable minidumps for parallel runs
            simulator.setRandomMode(false); // Deterministic for testing
            
            std::cout << "Starting test for category: " << categoryToString(cat) << " in thread " << i << "\n";
            try {
                simulator.runOnce();
            } catch (...) {
                std::cout << "Exception caught in thread " << i << " for category " << categoryToString(cat) << "\n";
            }
            std::cout << "Finished test for category: " << categoryToString(cat) << " in thread " << i << "\n";
        });
    }
    
    // Join all threads
    for (auto& t : threads) {
        t.join();
    }
    
    std::cout << "\nAll crash tests completed.\n";
    return 0;
}