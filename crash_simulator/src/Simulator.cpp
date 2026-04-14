#include "Simulator.hpp"
#include <iostream>
#include <thread>
#include <mutex>
#include <vector>
#include <cstring>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <fstream>      // ← AJOUTER : pour ofstream  ifstream
#include <iomanip>      // ← AJOUTER : pour std::put_time



#ifdef _WIN32
#include <windows.h>
#include <processthreadsapi.h>
#endif

namespace CrashSimulator {

Simulator* Simulator::instance_ = nullptr;

Simulator::Simulator() 
    : randomizer_(), 
      random_mode_(true), 
      intensity_(5), 
      logging_enabled_(true),
      generate_minidump_(true) {
    config_.random_mode = true;
    config_.intensity = 5;
    config_.generate_minidump = true;
    instance_ = this;
    


#ifdef _WIN32
    // Set unhandled exception handler for mini dump generation
    SetUnhandledExceptionFilter(unhandledExceptionHandler);
#endif
}

Simulator::Simulator(unsigned int seed)
    : randomizer_(seed), 
      random_mode_(true), 
      intensity_(5), 
      logging_enabled_(true),
      generate_minidump_(true) {
    config_.random_mode = true;
    config_.intensity = 5;
    config_.generate_minidump = true;
    instance_ = this;

#ifdef _WIN32
    // Set unhandled exception handler for mini dump generation
    SetUnhandledExceptionFilter(unhandledExceptionHandler);
#endif
}


Simulator::~Simulator() = default;

void Simulator::setCrashCategory(CrashCategory category) {
    config_.category = category; // config_.category = DIVISION_BY_ZERO
    random_mode_ = false;// 🔒 Disables random mode
}
//affich etiquette [Simulator] 
void Simulator::log(const std::string& message) {
    if (logging_enabled_) {
        std::cout << "[Simulator] " << message << std::endl;
    }
}
//capture all the information from a crash and save in CSV
void Simulator::recordCrash(CrashCategory category, const std::string& description, uint32_t exceptionCode) {
    last_report_.category = category;
    last_report_.seed = randomizer_.getSeed();
    last_report_.timestamp = std::chrono::system_clock::now();
    last_report_.description = description;
    last_report_.call_chain_depth = config_.recursion_depth;
    //last_report_.exception_code = exceptionCode;
    
    log("=== CRASH TRIGGERED ===");
    log("Category: " + categoryToString(category));
    log("Seed: " + std::to_string(last_report_.seed));
    log("Description: " + description);
    if (exceptionCode) {
        char hexBuf[32];
        snprintf(hexBuf, sizeof(hexBuf), "0x%08X", exceptionCode);
        log("Exception Code: " + std::string(hexBuf));
    }
    log("=======================");
      exportToCSV("crash_report.csv"); 
}


void Simulator::run() {
    log("Simulator started on Windows with seed: " + std::to_string(randomizer_.getSeed()));
    log("Intensity level: " + std::to_string(intensity_));
    
    if (random_mode_) {//If random mode is enabled
        while (true) {
            runOnce();//generates random crashes
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    } else {
        runOnce();//a single instance → triggers a specific crash.
    }
}

void Simulator::runOnce() {
    config_.seed = randomizer_.getSeed();
    config_.recursion_depth = randomizer_.getRandomRecursionDepth();
    config_.memory_size = randomizer_.getRandomMemorySize();
    config_.intensity = randomizer_.getRandomIntensity(1, intensity_);
    config_.generate_minidump = generate_minidump_;
    
    if (random_mode_) {
        config_.category = randomizer_.getRandomCrashCategory();
    }
      // Log the crash details for debugging and tracking
    log("Triggering crash: " + categoryToString(config_.category));
    log("Recursion depth: " + std::to_string(config_.recursion_depth));
    log("Intensity: " + std::to_string(config_.intensity));
    
    switch (config_.category) {
        case CrashCategory::SEGMENTATION_FAULT:
        case CrashCategory::ACCESS_VIOLATION:
            triggerAccessViolation();
            break;
        case CrashCategory::DIVISION_BY_ZERO:
            triggerDivisionByZero();
            break;
        case CrashCategory::ILLEGAL_INSTRUCTION:
            triggerIllegalInstruction();
            break;
        case CrashCategory::STACK_OVERFLOW:
            triggerStackOverflow();
            break;
        case CrashCategory::HEAP_CORRUPTION:
            triggerHeapCorruption();
            break;
        case CrashCategory::DEADLOCK:
            triggerDeadlock();
            break;
        case CrashCategory::ASSERTION_FAILURE:
            triggerAssertionFailure();
            break;
        case CrashCategory::RANDOM_MATH_FAULT:
            triggerRandomMathFault();
            break;
        case CrashCategory::SYSTEM_CALL_FAILURE:
            triggerSystemCallFailure();
            break;
        case CrashCategory::INVALID_HANDLE:
            triggerInvalidHandle();
            break;
        case CrashCategory::STACK_BUFFER_OVERFLOW:
            triggerStackBufferOverflow();
            break;
        default:
            break;
    }
}
//causes(provoque) a memory access violation
void Simulator::triggerAccessViolation() {
    // Step 1: Crash recording
    //Crash type identifier : access violation occurs when a program tries to access forbidden memory.
    recordCrash(CrashCategory::ACCESS_VIOLATION, "Intentional access violation", 0xC0000005);//Under Windows, the error code
    // Step 2: Random selection of the crash method
    int choice = randomizer_.getRandomIntensity(1, 3);
    // Step 3: Execute the chosen method
    switch (choice) {
        case 1: {
            // Null pointer dereference
            volatile int* ptr = nullptr;
            *ptr = 42;
            break;
        }
        case 2: {
            // Random invalid pointer
            volatile int* ptr = static_cast<int*>(randomizer_.getRandomPointer());
            *ptr = 42;
            break;
        }
        case 3: {
            // Write to read-only memory (Windows .rdata section)
            const char* rodata = "Read-only string";
            char* mutable_ptr = const_cast<char*>(rodata);
            mutable_ptr[0] = 'X';
            break;
        }
    }
}

void Simulator::triggerDivisionByZero() {
    recordCrash(CrashCategory::DIVISION_BY_ZERO, "Intentional integer division by zero", 0xC0000094);
    
    volatile int divisor = 0;
    volatile int result = 100 / divisor;
    (void)result;
}

void Simulator::triggerIllegalInstruction() {
    recordCrash(CrashCategory::ILLEGAL_INSTRUCTION, "Intentional illegal instruction", 0xC000001D);
    
#ifdef _WIN32
    // On Windows, we can use RaiseException
    RaiseException(0xC000001D, EXCEPTION_NONCONTINUABLE, 0, nullptr);
#else
    // Create a function pointer to invalid memory
    using void_func_t = void(*)();
    void_func_t invalid_func = reinterpret_cast<void_func_t>(randomizer_.getRandomPointer());
    invalid_func();
#endif
}

void Simulator::deepRecurse(int depth) {
    if (depth <= 0) {/// Step 1: Stopping condition
        // Trigger crash at maximum depth
        triggerAccessViolation();
        return;
    }
    
    // U4 KB allocation on the stack
    volatile char buffer[4096];
    for (int i = 0; i < 4096; ++i) {
        buffer[i] = static_cast<char>(i % 256);// Force the real writing
    }
    
    deepRecurse(depth - 1);// We recall using depth-1
}
// provoquer un Stack Overflow
void Simulator::triggerStackOverflow() {
   // Crash recorded in logs/CSV
    recordCrash(CrashCategory::STACK_OVERFLOW, 
                "Intentional stack overflow with depth " + std::to_string(config_.recursion_depth),
                0xC00000FD);
    //depth calculation
    int depth = config_.recursion_depth * intensity_;
    //Safety limits (min/max)
    if (depth < 10) depth = 10;
    if (depth > 500) depth = 500;
    
    deepRecurse(depth);
}
//writing beyond the limits of an allocated array.
void Simulator::corruptHeapBlock() {
    //Allocate a memory block on the heap
    size_t size = config_.memory_size;
    char* buffer = new char[size];
    
    // Write beyond bounds based on intensity
    size_t corruption_offset = size + (randomizer_.getRandomIntensity(1, intensity_) * 100);
    

    
    // Use VirtualProtect to make it more interesting on Windows
#ifdef _WIN32
    DWORD oldProtect;
    VirtualProtect(buffer + corruption_offset - 4096, 4096, PAGE_READWRITE, &oldProtect);
#endif
//WRITE OUT OF Boundaries → heap corruption    
    buffer[corruption_offset] = 0xFF;
    //Freeing the memory → the crash occurs
    delete[] buffer;
}

void Simulator::createUseAfterFree() {
    size_t size = config_.memory_size;
    int* array = new int[size / sizeof(int)];
    
    for (size_t i = 0; i < size / sizeof(int); ++i) {
        array[i] = randomizer_.getRandomIntensity(0, 1000);
    }
    
    delete[] array;
    
    // Use after free
    array[0] = 42;
}

void Simulator::doubleFree() {
    int* ptr = new int(42);
    delete ptr;
    delete ptr;  // Double free
}

void Simulator::triggerHeapCorruption() {
    recordCrash(CrashCategory::HEAP_CORRUPTION, 
                "Intentional heap corruption with size " + std::to_string(config_.memory_size),
                0xC0000374);
    
    int choice = randomizer_.getRandomIntensity(1, 3);
    
    switch (choice) {
        case 1:
            corruptHeapBlock();
            break;
        case 2:
            createUseAfterFree();
            break;
        case 3:
            doubleFree();
            break;
    }
}
//causes an infinite blockage
void Simulator::infiniteLoop() {
    volatile int counter = 0;
    while (true) {
        ++counter;
        if (counter < 0) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
//cause a blockage by using a mutex
void Simulator::recursiveMutexLock() {
    static std::recursive_mutex mtx;
    std::lock_guard<std::recursive_mutex> lock(mtx);
    recursiveMutexLock();
}

void Simulator::triggerDeadlock() {
    recordCrash(CrashCategory::DEADLOCK, "Intentional deadlock/infinite loop");
    
    int choice = randomizer_.getRandomIntensity(1, 2);
    
    switch (choice) {
        case 1:
            infiniteLoop();
            break;
        case 2:
            recursiveMutexLock();
            break;
    }
}

void Simulator::triggerAssertionFailure() {
    recordCrash(CrashCategory::ASSERTION_FAILURE, "Intentional assertion failure", 0x40010006);
    
#ifdef _WIN32
    // Use RaiseException for assertion failure
    RaiseException(0x40010006, EXCEPTION_NONCONTINUABLE, 0, nullptr);
#else
    std::raise(SIGABRT);
#endif
}

void Simulator::randomNumberTableFault() {
    size_t table_size = 100 + randomizer_.getRandomIntensity(1, intensity_) * 50;
    std::vector<int> numbers(table_size);
    
    // Fill with random numbers
    for (size_t i = 0; i < table_size; ++i) {
        numbers[i] = randomizer_.getRandomIntensity(-100, 100);
    }
    
    // Introduce a zero at random position based on intensity
    if (randomizer_.getRandomIntensity(1, 10) <= intensity_) {
        size_t zero_pos = randomizer_.getRandomIntensity(0, static_cast<int>(table_size - 1));
        numbers[zero_pos] = 0;
        log("Introduced zero at position " + std::to_string(zero_pos));
    }
    
    // Compute multiplicative inverses
    for (size_t i = 0; i < table_size; ++i) {
        if (numbers[i] == 0) {
            log("Division by zero detected at position " + std::to_string(i));
            volatile int result = 100 / numbers[i];
            (void)result;
        }
    }
}

void Simulator::multiplicativeInverseCrash() {
    const size_t array_size = 50;
    int numbers[50];
    
    // Initialize with pattern that may include zero
    for (size_t i = 0; i < array_size; ++i) {
        int base = randomizer_.getRandomIntensity(1, 100);
        if (randomizer_.getRandomIntensity(1, 100) <= intensity_ * 10) {
            numbers[i] = 0;  // Introduce zero
        } else {
            numbers[i] = base;
        }
    }
    
    // Attempt to compute inverses
    for (size_t i = 0; i < array_size; ++i) {
        if (numbers[i] == 0) {
            volatile int result = 1 / numbers[i];
            (void)result;
        }
    }
}

void Simulator::triggerRandomMathFault() {
    recordCrash(CrashCategory::RANDOM_MATH_FAULT, "Intentional random math fault");
    
    int choice = randomizer_.getRandomIntensity(1, 2);
    
    switch (choice) {
        case 1:
            randomNumberTableFault();
            break;
        case 2:
            multiplicativeInverseCrash();
            break;
    }
}

void Simulator::triggerSystemCallFailure() {
    recordCrash(CrashCategory::SYSTEM_CALL_FAILURE, "Intentional system call failure");
    
    // Force malloc to fail with huge allocation
    size_t huge_size = SIZE_MAX / 2;
    void* ptr = malloc(huge_size);
    if (ptr == nullptr) {
        // Use the null pointer to cause crash
        volatile char* crash_ptr = static_cast<char*>(ptr);
        *crash_ptr = 'X';
    }
}

void Simulator::triggerInvalidHandle() {
    recordCrash(CrashCategory::INVALID_HANDLE, "Intentional invalid handle usage");
    
#ifdef _WIN32
    // Use an invalid handle
    HANDLE invalidHandle = reinterpret_cast<HANDLE>(0x12345678);
    CloseHandle(invalidHandle);
#else
    // POSIX equivalent - invalid file descriptor
    int invalid_fd = 999999;
    close(invalid_fd);
#endif
}

void Simulator::corruptStackBuffer() {
    char buffer[64];
    
    // Copy more than buffer size based on intensity
    size_t copy_size = 64 + (randomizer_.getRandomIntensity(1, intensity_) * 10);
    std::string large_string(copy_size, 'A');
    
    std::memcpy(buffer, large_string.c_str(), copy_size);
}

void Simulator::triggerStackBufferOverflow() {
    recordCrash(CrashCategory::STACK_BUFFER_OVERFLOW, 
                "Intentional stack buffer overflow with size " + std::to_string(config_.memory_size));
    
    corruptStackBuffer();
}
  

// ═════════════════════════════════════════════════════════════════════════════
//  CSV Export - Sauvegarde du rapport de crash
// ═════════════════════════════════════════════════════════════════════════════

bool Simulator::exportToCSV(const std::string& filename) {
    std::ofstream csv(filename, std::ios::app);  // Mode append
    if (!csv.is_open()) {
        log("ERROR: Cannot open CSV file: " + filename);
        return false;
    }
    
    // Vérifier si le fichier est vide pour écrire l'en-tête
    csv.seekp(0, std::ios::end);
    bool isEmpty = (csv.tellp() == 0);
    
    // Écrire l'en-tête si fichier nouveau
    if (isEmpty) {
        csv << "timestamp,unix_timestamp,category,category_name,seed,"
            << "description,call_chain_depth,exception_code,intensity,"
            << "recursion_depth,memory_size,random_mode,generate_minidump\n";
    }
    
    // Formater le timestamp
    auto time_t_timestamp = std::chrono::system_clock::to_time_t(last_report_.timestamp);
    std::tm tm_timestamp;
#ifdef _WIN32
    localtime_s(&tm_timestamp, &time_t_timestamp);
#else
    localtime_r(&time_t_timestamp, &tm_timestamp);
#endif
    
    char timestamp_buf[32];
    std::strftime(timestamp_buf, sizeof(timestamp_buf), "%Y-%m-%d %H:%M:%S", &tm_timestamp);
    
    // Écrire la ligne de données
    csv << "\"" << timestamp_buf << "\","                    // timestamp
        << time_t_timestamp << ","                           // unix_timestamp
        << static_cast<int>(last_report_.category) << ","    // category (ID)
        << "\"" << categoryToString(last_report_.category) << "\","  // category_name
        << last_report_.seed << ","                          // seed
        << "\"" << last_report_.description << "\","         // description
        << last_report_.call_chain_depth << ","              // call_chain_depth
       // << last_report_.exception_code << ","                // exception_code
        << config_.intensity << ","                          // intensity
        << config_.recursion_depth << ","                    // recursion_depth
        << config_.memory_size << ","                        // memory_size
        << (config_.random_mode ? "true" : "false") << ","   // random_mode
        << (config_.generate_minidump ? "true" : "false")    // generate_minidump
        << "\n";
    
    csv.close();
    
    if (logging_enabled_) {
        log("CSV report saved to: " + filename);
    }
    
    return true;
}

#ifdef _WIN32
void Simulator::generateMiniDump(EXCEPTION_POINTERS* exceptionInfo) {
    if (!generate_minidump_) return;
    
    // Create dump file
    SYSTEMTIME st;
    GetSystemTime(&st);
    
    char dumpPath[MAX_PATH];
    sprintf_s(dumpPath, "crash_dump_%04d%02d%02d_%02d%02d%02d.dmp",
              st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    
    HANDLE hFile = CreateFileA(dumpPath, GENERIC_WRITE, 0, NULL,
                                CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    
    if (hFile != INVALID_HANDLE_VALUE) {
        MINIDUMP_EXCEPTION_INFORMATION mdei;
        mdei.ThreadId = GetCurrentThreadId();
        mdei.ExceptionPointers = exceptionInfo;
        mdei.ClientPointers = FALSE;
        
        // Fixed: Use explicit cast for MINIDUMP_TYPE
        MINIDUMP_TYPE mdt = static_cast<MINIDUMP_TYPE>(
            MiniDumpWithDataSegs | MiniDumpWithHandleData | 
            MiniDumpWithThreadInfo | MiniDumpWithProcessThreadData);
        
        BOOL result = MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(),
                                         hFile, mdt, 
                                         (exceptionInfo != nullptr) ? &mdei : nullptr,
                                         nullptr, nullptr);
        
        if (result) {
            log("Mini dump saved to: " + std::string(dumpPath));
        } else {
            log("Failed to save mini dump. Error: " + std::to_string(GetLastError()));
        }
        
        CloseHandle(hFile);
    }
}

LONG WINAPI Simulator::unhandledExceptionHandler(EXCEPTION_POINTERS* exceptionInfo) {
    if (instance_) {
        instance_->generateMiniDump(exceptionInfo);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
#endif

} // namespace CrashSimulator