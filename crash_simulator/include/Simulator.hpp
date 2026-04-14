#pragma once

#include "CrashTypes.hpp"
#include "Randomizer.hpp"
#include <memory>
#include <string>
#include <vector>
#include <algorithm> // <-- OBLIGATOIRE pour std::clamp
#ifdef _WIN32
#include <windows.h>
#include <dbghelp.h>
#endif

namespace CrashSimulator {

class Simulator {
public:
    Simulator();
    explicit Simulator(unsigned int seed);
    ~Simulator();
    
    // Configuration
    void setRandomMode(bool enabled) { random_mode_ = enabled; }
    void setCrashCategory(CrashCategory category);
    void setIntensity(int intensity) { intensity_ = std::clamp(intensity, 1, 10); } // Clamp intensity to [1, 10]
    void enableLogging(bool enabled) { logging_enabled_ = enabled; }
    void setGenerateMinidump(bool enabled) { generate_minidump_ = enabled; }
    
    // Execution
    void run();
    void runOnce();
    
    // Crash generators
    void triggerAccessViolation();
    void triggerDivisionByZero();
    void triggerIllegalInstruction();
    void triggerStackOverflow();
    void triggerHeapCorruption();
    void triggerDeadlock();
    void triggerAssertionFailure();
    void triggerRandomMathFault();
    void triggerSystemCallFailure();
    void triggerInvalidHandle();
    void triggerStackBufferOverflow();
    
    // Statistics (UNE SEULE FOIS CHACUN)
    const CrashReport& getLastReport() const { return last_report_; }
    unsigned int getCurrentSeed() const { return randomizer_.getSeed(); }
    
    // CSV Export (UNE SEULE FOIS)
    bool exportToCSV(const std::string& filename = "crash_report.csv");
    
#ifdef _WIN32
    // Mini dump generation
    void generateMiniDump(EXCEPTION_POINTERS* exceptionInfo);
    static LONG WINAPI unhandledExceptionHandler(EXCEPTION_POINTERS* exceptionInfo);
#endif
private:
    Randomizer randomizer_;
    CrashConfig config_;
    CrashReport last_report_;
    bool random_mode_;
    int intensity_;
    bool logging_enabled_;
    bool generate_minidump_;
    
    // Internal helpers
    void log(const std::string& message);
    void recordCrash(CrashCategory category, const std::string& description, uint32_t exceptionCode = 0);
    
    // Deep recursion helper
    void deepRecurse(int depth);
    
    // Heap corruption helpers
    void corruptHeapBlock();
    void createUseAfterFree();
    void doubleFree();
    
    // Deadlock helpers
    void infiniteLoop();
    void recursiveMutexLock();
    
    // Math fault helpers
    void randomNumberTableFault();
    void multiplicativeInverseCrash();
    
    // Buffer overflow helpers
    void corruptStackBuffer();
    
    static Simulator* instance_;
};

} // namespace CrashSimulator