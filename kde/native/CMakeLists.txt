cmake_minimum_required(VERSION 3.20)
project(mcglass LANGUAGES CXX)

# Tiny C ABI over KWindowEffects so the Python app can ask KWin to blur the
# desktop behind its translucent window.
find_package(Qt6 REQUIRED COMPONENTS Gui)
find_package(KF6WindowSystem REQUIRED)

add_library(mcglass SHARED mcglass.cpp)
target_link_libraries(mcglass PRIVATE Qt6::Gui KF6::WindowSystem)
set_target_properties(mcglass PROPERTIES
    CXX_STANDARD 17
    CXX_VISIBILITY_PRESET hidden
    PREFIX "lib")
