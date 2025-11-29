cmake_minimum_required(VERSION 3.16)

project(Thirdparty LANGUAGES C CXX)

set(D ${CMAKE_CURRENT_SOURCE_DIR})

include(FetchContent)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# OPENGL
set(OPENGL_LIBS)
if(WIN32)
    list(APPEND OPENGL_LIBS opengl32)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
elseif(UNIX AND NOT APPLE)
    find_package(OpenGL REQUIRED)
    add_definitions(${OPENGL_DEFINITIONS})
    list(APPEND OPENGL_LIBS OpenGL::OpenGL)
elseif(APPLE)
    find_library(COCOA_LIBRARY Cocoa)
    find_library(IOKIT_LIBRARY IOKit)
    find_library(COREVIDEO_LIBRARY CoreVideo)
    set(OPENGL_LIBS ${COCOA_LIBRARY} ${IOKIT_LIBRARY} ${COREVIDEO_LIBRARY} "-framework OpenGL")
endif()

# GLAD
set(GLAD_DIR ${D}/glad)
set(GLAD_INCLUDE_DIR ${GLAD_DIR}/include)
add_library(glad INTERFACE)
target_sources(glad INTERFACE ${GLAD_DIR}/src/glad.c)
target_include_directories(glad SYSTEM INTERFACE ${GLAD_INCLUDE_DIR})
set_property(TARGET glad PROPERTY FOLDER "Thirdparty")

# GLFW
option(GLFW_BUILD_DOCS "Build GLFW documentation" OFF)
option(GLFW_BUILD_TESTS "Build GLFW tests" OFF)
option(GLFW_BUILD_EXAMPLES "Build GLFW examples" OFF)
option(GLFW_INSTALL "Generate installation target" OFF)


FetchContent_Declare(
    glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG 3.4
)

set(GLFW_BUILD_DOCS OFF CACHE BOOL "Build GLFW documentation")
set(GLFW_BUILD_TESTS OFF CACHE BOOL "Build GLFW tests")
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "Build GLFW examples")
set(GLFW_INSTALL OFF CACHE BOOL "Generate installation target")

FetchContent_MakeAvailable(glfw)

if (TARGET update_mappings)
    set_target_properties(update_mappings PROPERTIES FOLDER "Thirdparty")
endif()
set_property(TARGET glfw PROPERTY FOLDER "Thirdparty")

# IMGUI
FetchContent_Declare(
    imgui
    GIT_REPOSITORY https://github.com/ocornut/imgui.git
    GIT_TAG docking
)
FetchContent_MakeAvailable(imgui)
if(NOT TARGET imgui)
    file(GLOB IMGUI_SOURCES 
        ${imgui_SOURCE_DIR}/*.cpp
        ${imgui_SOURCE_DIR}/backends/imgui_impl_glfw.cpp
        ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp
    )
    
    add_library(imgui STATIC ${IMGUI_SOURCES})
    
    target_include_directories(imgui PUBLIC 
        ${imgui_SOURCE_DIR}
        ${imgui_SOURCE_DIR}/backends
    )
    
    target_link_libraries(imgui PRIVATE glfw ${OPENGL_LIBS})
    
    if(APPLE)
        target_compile_definitions(imgui PRIVATE GL_SILENCE_DEPRECATION)
    endif() 
    set_property(TARGET imgui PROPERTY FOLDER "Thirdparty")
endif()

# NLOHMANN JSON
option(JSON_BuildTests "Build the JSON test suite" OFF)
option(JSON_Install "Install the JSON library" OFF)
option(JSON_MultipleHeaders "Use multiple headers instead of single header" OFF)

FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.12.0
)

set(JSON_BuildTests OFF CACHE BOOL "Disable tests" FORCE)
set(JSON_Install OFF CACHE BOOL "Disable installation" FORCE)
set(JSON_MultipleHeaders OFF CACHE BOOL "Use single header" FORCE)

FetchContent_MakeAvailable(nlohmann_json)

if(NOT TARGET nlohmann_json::nlohmann_json)
    if(TARGET nlohmann_json)
        add_library(nlohmann_json::nlohmann_json ALIAS nlohmann_json)
    else()
        add_library(nlohmann_json INTERFACE)
        target_include_directories(nlohmann_json INTERFACE 
            ${nlohmann_json_SOURCE_DIR}/include
        )
        add_library(nlohmann_json::nlohmann_json ALIAS nlohmann_json)
    endif()
endif()

set_property(TARGET nlohmann_json PROPERTY FOLDER "Thirdparty")

# CPR
FetchContent_Declare(
    cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr
    GIT_TAG 1.13.0
)

FetchContent_MakeAvailable(cpr)

set_property(TARGET cpr PROPERTY FOLDER "Thirdparty")

# LEXBOR
option(LEXBOR_BUILD_SHARED "" OFF)
option(LEXBOR_BUILD_STATIC "" ON)

FetchContent_Declare(
    lexbor
    GIT_REPOSITORY https://github.com/lexbor/lexbor
    GIT_TAG v2.6.0
)

set(LEXBOR_BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(LEXBOR_BUILD_STATIC ON CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(lexbor)

set_property(TARGET lexbor_static PROPERTY FOLDER "Thirdparty")

# CEF
add_subdirectory(cef)


function(link_thirdparty TARGET_NAME)
    add_library(Thirdparty INTERFACE)
    target_link_libraries(Thirdparty INTERFACE glad glfw imgui nlohmann_json cpr lexbor_static)
    target_include_directories(Thirdparty INTERFACE
        ${glad_SOURCE_DIR}/include
        ${glfw_SOURCE_DIR}/include
        ${zlib_SOURCE_DIR}
        ${imgui_SOURCE_DIR}
        ${imgui_SOURCE_DIR}/backends
        ${nlohmann_json_SOURCE_DIR}/include
        ${lexbor_SOURCE_DIR}/source
        ${curl_SOURCE_DIR}/include
        ${libpsl_SOURCE_DIR}/include
        ${cpr_SOURCE_DIR}/include
    )

    target_link_libraries(${TARGET_NAME} PRIVATE Thirdparty)
    if(APPLE)
        target_link_options(${TARGET_NAME} PRIVATE 
            -framework Cocoa
            -framework IOKit
            -framework CoreVideo
            -framework OpenGL
        )
    endif()
endfunction()

message(STATUS "Thirdparty configuration complete:")
message(STATUS "  - GLAD: ${GLAD_DIR}")
message(STATUS "  - GLFW: ${glfw_SOURCE_DIR}")
message(STATUS "  - ImGui: ${imgui_SOURCE_DIR}")
message(STATUS "  - nlohmann/json: ${nlohmann_json_SOURCE_DIR}")
message(STATUS "  - Lexbor: ${lexbor_SOURCE_DIR}")
message(STATUS "  - cpr: ${cpr_SOURCE_DIR}")

