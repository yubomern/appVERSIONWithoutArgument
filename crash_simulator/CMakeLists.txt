cmake_minimum_required(VERSION 3.10)
project(CrashSimulator VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows specific settings
if(WIN32)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-D_WIN32_WINNT=0x0601)
endif()

# Directories
set(INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)
set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Executable
add_executable(crash-simulator
    ${SRC_DIR}/main.cpp
    ${SRC_DIR}/Randomizer.cpp
    ${SRC_DIR}/Simulator.cpp
)

target_include_directories(crash-simulator PRIVATE ${INCLUDE_DIR})

# Compiler options
if(MSVC)
    target_compile_options(crash-simulator PRIVATE /W4 /O2 /EHsc /wd4996)
else()
    target_compile_options(crash-simulator PRIVATE -Wall -Wextra -O2)
endif()

# Link libraries
if(WIN32)
    target_link_libraries(crash-simulator PRIVATE 
        dbghelp 
        psapi 
    )
endif()