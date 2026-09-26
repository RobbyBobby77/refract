cmake_minimum_required(VERSION 3.20)
project(refract_effects LANGUAGES CXX)

# Tiny C ABI over KWindowEffects so the Python app can ask KWin to blur the
# desktop behind its translucent window.
find_package(Qt6 REQUIRED COMPONENTS Gui)
find_package(KF6WindowSystem REQUIRED)

add_library(refract_effects SHARED refract_effects.cpp)
target_link_libraries(refract_effects PRIVATE Qt6::Gui KF6::WindowSystem)
set_target_properties(refract_effects PROPERTIES
    CXX_STANDARD 17
    CXX_VISIBILITY_PRESET hidden
    PREFIX "lib")
