cmake_minimum_required(VERSION 3.16)
project(CoreDumpPFE VERSION 2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

# ════════════════════════════════════════════════════════════════════════════
#  Build crash_simulator as subdirectory
# ════════════════════════════════════════════════════════════════════════════

add_subdirectory(crash_simulator)

# ════════════════════════════════════════════════════════════════════════════
#  Build test executables at root level
# ════════════════════════════════════════════════════════════════════════════

# test_crash_csv_analyzer - Standalone CSV analyzer
add_executable(test_crash_csv_analyzer
    test/test_crash_csv_analyzer.cpp
)

target_include_directories(test_crash_csv_analyzer PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/crash_simulator/include
)

set_target_properties(test_crash_csv_analyzer PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/test
)

# ════════════════════════════════════════════════════════════════════════════
#  Register tests with CTest
# ════════════════════════════════════════════════════════════════════════════

add_test(NAME csv_analyzer_test COMMAND test_crash_csv_analyzer 
    ${CMAKE_BINARY_DIR}/crash_simulator/build/crash_report.csv
)

# ════════════════════════════════════════════════════════════════════════════
#  Platform-specific configurations
# ════════════════════════════════════════════════════════════════════════════

if(WIN32)
    # Windows-specific settings
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
    add_compile_definitions(_WIN32_WINNT=0x0601)
elseif(UNIX AND NOT APPLE)
    # Linux-specific settings
    find_package(Threads REQUIRED)
endif()

# ════════════════════════════════════════════════════════════════════════════
#  Custom targets for convenience
# ════════════════════════════════════════════════════════════════════════════

# Target to run all tests
add_custom_target(run_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
    DEPENDS test_crash_csv_analyzer
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Running all tests..."
)

# Target to generate documentation (if needed)
add_custom_target(docs
    COMMAND ${CMAKE_COMMAND} -E echo "Documentation generation placeholder"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating documentation..."
)

# ════════════════════════════════════════════════════════════════════════════
#  Installation rules
# ════════════════════════════════════════════════════════════════════════════

install(TARGETS test_crash_csv_analyzer
    RUNTIME DESTINATION bin
)

# Install crash_simulator targets if they exist
install(DIRECTORY crash_simulator/include/
    DESTINATION include/crash_simulator
    FILES_MATCHING PATTERN "*.hpp"
)

# ════════════════════════════════════════════════════════════════════════════
#  Summary
# ════════════════════════════════════════════════════════════════════════════

message(STATUS "")
message(STATUS "╔═══════════════════════════════════════════════════════════╗")
message(STATUS "║         CoreDump PFE v${PROJECT_VERSION} - Build Config          ║")
message(STATUS "╠═══════════════════════════════════════════════════════════╣")
message(STATUS "║  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "║  Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "║  Platform: ${CMAKE_SYSTEM_NAME}")
message(STATUS "║  Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "╚═══════════════════════════════════════════════════════════╝")
message(STATUS "")