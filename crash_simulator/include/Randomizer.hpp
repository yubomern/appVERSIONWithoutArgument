#pragma once

#include "CrashTypes.hpp"
#include <random>
#include <vector>
#include <memory>

namespace CrashSimulator {

class Randomizer {
public:
    explicit Randomizer(unsigned int seed = std::random_device{}());
    
    CrashCategory getRandomCrashCategory();
    int getRandomRecursionDepth(int minDepth = 3, int maxDepth = 20);
    size_t getRandomMemorySize(size_t minSize = 1024, size_t maxSize = 1024 * 1024);
    void* getRandomPointer();
    int getRandomIntensity(int minIntensity = 1, int maxIntensity = 10);
    uint32_t getRandomExceptionCode();
    
    unsigned int getSeed() const { return seed_; }
    void setSeed(unsigned int seed) { 
        seed_ = seed; 
        rng_.seed(seed_);
    }
    
    // Weighted probability for crash categories
    void setCategoryWeights(const std::vector<double>& weights);
    
private:
    unsigned int seed_;
    std::mt19937 rng_;
    std::vector<double> category_weights_;
    
    void initializeDefaultWeights();
};

} // namespace CrashSimulator