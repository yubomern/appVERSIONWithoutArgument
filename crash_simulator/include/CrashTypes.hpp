#pragma once

#include <string>
#include <random>
#include <chrono>
#include <cstdint>

namespace CrashSimulator {

enum class CrashCategory : uint32_t {
    SEGMENTATION_FAULT = 0,
    DIVISION_BY_ZERO,
    ILLEGAL_INSTRUCTION,
    STACK_OVERFLOW,
    HEAP_CORRUPTION,
    DEADLOCK,
    ASSERTION_FAILURE,
    RANDOM_MATH_FAULT,
    SYSTEM_CALL_FAILURE,
    ACCESS_VIOLATION,
    INVALID_HANDLE,
    STACK_BUFFER_OVERFLOW,
    COUNT  // Must be last
};

struct CrashConfig {
    CrashCategory category;
    unsigned int seed;
    int recursion_depth;
    size_t memory_size;
    bool random_mode;
    int intensity;  // 1-10
    bool generate_minidump;
};

struct CrashReport {
    CrashCategory category;
    unsigned int seed;
    std::chrono::system_clock::time_point timestamp;
    std::string description;
    int call_chain_depth;
    uint32_t exception_code;      // Added for Windows exception handling
    std::string exception_address;
    
    
    CrashReport() : category(CrashCategory::SEGMENTATION_FAULT), seed(0), 
                    call_chain_depth(0), exception_code(0) {}
};

inline std::string categoryToString(CrashCategory cat) {
    switch (cat) {
        case CrashCategory::SEGMENTATION_FAULT: return "Segmentation Fault";
        case CrashCategory::DIVISION_BY_ZERO: return "Integer Division by Zero";
        case CrashCategory::ILLEGAL_INSTRUCTION: return "Illegal Instruction";
        case CrashCategory::STACK_OVERFLOW: return "Stack Overflow";
        case CrashCategory::HEAP_CORRUPTION: return "Heap Corruption";
        case CrashCategory::DEADLOCK: return "Deadlock / Infinite Loop";
        case CrashCategory::ASSERTION_FAILURE: return "Assertion Failure";
        case CrashCategory::RANDOM_MATH_FAULT: return "Random Math Fault";
        case CrashCategory::SYSTEM_CALL_FAILURE: return "System Call Failure";
        case CrashCategory::ACCESS_VIOLATION: return "Access Violation";
        case CrashCategory::INVALID_HANDLE: return "Invalid Handle Usage";
        case CrashCategory::STACK_BUFFER_OVERFLOW: return "Stack Buffer Overflow";
        default: return "Unknown";
    }
}

} // namespace CrashSimulator