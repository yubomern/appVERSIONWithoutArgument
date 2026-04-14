#include "Randomizer.hpp"
#include <algorithm>

namespace CrashSimulator {

Randomizer::Randomizer(unsigned int seed) 
    : seed_(seed), rng_(seed_) {
    initializeDefaultWeights();
}

void Randomizer::initializeDefaultWeights() {
    category_weights_ = {
        0.12,  // SEGMENTATION_FAULT
        0.08,  // DIVISION_BY_ZERO
        0.08,  // ILLEGAL_INSTRUCTION
        0.10,  // STACK_OVERFLOW
        0.12,  // HEAP_CORRUPTION
        0.05,  // DEADLOCK
        0.08,  // ASSERTION_FAILURE
        0.12,  // RANDOM_MATH_FAULT
        0.08,  // SYSTEM_CALL_FAILURE
        0.07,  // ACCESS_VIOLATION
        0.05,  // INVALID_HANDLE
        0.05   // STACK_BUFFER_OVERFLOW
    };
}

void Randomizer::setCategoryWeights(const std::vector<double>& weights) {
    if (weights.size() == static_cast<size_t>(CrashCategory::COUNT)) {
        category_weights_ = weights;
    }
}

CrashCategory Randomizer::getRandomCrashCategory() {
    std::discrete_distribution<> dist(category_weights_.begin(), category_weights_.end());
    return static_cast<CrashCategory>(dist(rng_));
}

int Randomizer::getRandomRecursionDepth(int minDepth, int maxDepth) {
    std::uniform_int_distribution<int> dist(minDepth, maxDepth);
    return dist(rng_);
}

size_t Randomizer::getRandomMemorySize(size_t minSize, size_t maxSize) {
    std::uniform_int_distribution<size_t> dist(minSize, maxSize);
    return dist(rng_);
}

void* Randomizer::getRandomPointer() {
    std::uniform_int_distribution<uintptr_t> dist(1, UINTPTR_MAX - 1);
    return reinterpret_cast<void*>(dist(rng_));
}

int Randomizer::getRandomIntensity(int minIntensity, int maxIntensity) {
    std::uniform_int_distribution<int> dist(minIntensity, maxIntensity);
    return dist(rng_);
}

uint32_t Randomizer::getRandomExceptionCode() {
    std::vector<uint32_t> exception_codes = {
        0xC0000005,  // EXCEPTION_ACCESS_VIOLATION
        0xC0000094,  // EXCEPTION_INT_DIVIDE_BY_ZERO
        0xC0000095,  // EXCEPTION_INT_OVERFLOW
        0xC000001D,  // EXCEPTION_ILLEGAL_INSTRUCTION
        0xC00000FD,  // EXCEPTION_STACK_OVERFLOW
        0xC0000374,  // HEAP_CORRUPTION
        0x40010006   // ASSERTION_FAILURE
    };
    std::uniform_int_distribution<size_t> dist(0, exception_codes.size() - 1);
    return exception_codes[dist(rng_)];
}

} // namespace CrashSimulator