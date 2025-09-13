cmake_minimum_required(VERSION 3.16)

project(JurisData LANGUAGES C CXX)

if (${CMAKE_BINARY_DIR} STREQUAL ${CMAKE_SOURCE_DIR})
    message(FATAL_ERROR "Compilation inside source folder not allowed. Use a build folder.")
endif()

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug CACHE STRING "Choose the type of build" FORCE)
endif(NOT CMAKE_BUILD_TYPE)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if (NOT MSVC)
    # globally set -fno-strict-aliasing, needed due to using reinterpret_cast
      add_compile_options(-fno-strict-aliasing -finput-charset=UTF-8 -fexec-charset=UTF-8 -fno-char8_t)
endif()

if(MSVC)
    add_compile_options(/std:c++20 /MP /utf-8 /Zc:char8_t-)
    add_link_options(/ignore:4099)
endif()

if (WIN32)
    add_definitions(-DUNICODE -D_UNICODE)
endif()

# create bin folder
file(MAKE_DIRECTORY bin)

set(BIN_DIR ${CMAKE_SOURCE_DIR}/bin)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${BIN_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${BIN_DIR}/lib)

if (LINUX AND NOT APPLE)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${BIN_DIR}/lib/${CMAKE_BUILD_TYPE})
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${BIN_DIR}/lib/${CMAKE_BUILD_TYPE})
endif()

include_directories(Source)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR})
if (LINUX AND NOT APPLE)
	set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR}/${CMAKE_BUILD_TYPE})
endif()

if(WIN32)
    set(VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
endif()

file(GLOB_RECURSE JD_SOURCES "Source/**.cpp" "Source/**.h" "Source/**.inl")
add_executable(${PROJECT_NAME} ${JD_SOURCES})
if(WIN32)
    target_link_libraries(${PROJECT_NAME} ws2_32)
endif()