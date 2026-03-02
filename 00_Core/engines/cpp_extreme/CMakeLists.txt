cmake_minimum_required(VERSION 3.10)
project(HCB_Bridge_System)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

add_library(hcb_bridge SHARED src/hcb_bridge.cpp)

set_target_properties(hcb_bridge PROPERTIES 
    LINKER_LANGUAGE CXX
    PREFIX ""
)