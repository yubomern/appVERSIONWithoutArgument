# Crash Simulator Project Description

## Overview
The Crash Simulator is a Windows-based fault generation tool designed for embedded systems testing. It intentionally triggers various types of crashes to simulate real-world failure scenarios for debugging and testing purposes.

## Recent Changes (April 14, 2026)

### Code Modifications
- **Removed Command-Line Argument Parsing**: Eliminated all argument handling logic from `main.cpp`, including Windows-specific `ParseCommandLine` function and Unix `getopt_long` implementation.
- **Parallel Test Execution**: Modified the main function to run all 12 crash categories simultaneously in separate threads:
  - Each crash type (Segmentation Fault, Division by Zero, Illegal Instruction, etc.) runs in its own thread
  - Threads are created using `std::thread` and managed with `std::vector`
  - All threads are joined before program exit
  - Added try-catch blocks for exception handling
- **Constructor Enhancement**: Added `Simulator::Simulator(unsigned int seed)` constructor to support seeded initialization for deterministic testing.

### Technical Details
- **Threading**: Uses C++11 threading features for parallel execution
- **Crash Categories**: Supports 12 different crash types (0-11)
- **Deterministic Mode**: Each thread uses a unique seed for reproducible crashes
- **No Arguments Required**: Program runs automatically without user input

### Build and Testing
- **Build System**: CMake-based build with MSVC compiler
- **Test Suite**: Includes CTest integration with CSV analyzer test
- **Output**: Generates crash reports in CSV format (when enabled)

### Usage
Run the executable without arguments:
```bash
./crash-simulator.exe
```

The program will automatically execute all crash tests in parallel and display results.

### Files Modified
- `crash_simulator/src/main.cpp`: Main entry point with threading logic
- `crash_simulator/src/Simulator.cpp`: Added seeded constructor

### Dependencies
- C++17 standard
- Windows API (for crash simulation)
- CMake 3.16+ for building

## Project Structure
```
├── CMakeLists.txt                 # Root build configuration
├── crash_simulator/               # Main simulator module
│   ├── CMakeLists.txt
│   ├── include/                   # Header files
│   └── src/                       # Source files
├── test/                          # Test executables
├── build/                         # Build output directory
└── docs/                          # Documentation
```


"""


class  namespace  = custom == class struct  ,   namespace app::AppData  , 
CrashSimulator::recordCrash  ()
cv.   reference   // passage par variable modifable 
cv :: static 
cv->  pointer  //passage par variable ;

&memoire  variable 
a = 0x0258 
b = 0x0589
&a  ;  a = 1 
&b ;  b = 2 
*(&a)  =  a 
"""
*p = &a
a= 5 
&a = 0x5852 
p = &a = 0x585 
*p =  a =  5 
*p = a 
a = *p 



1 + 1  =   2    //   ok 


assert   1 +1 ==  2  //  c++   assert juste  ,    assert  failure   ,  c ++ 
