cmake_minimum_required(VERSION 3.21)

project(hakoniwa-robot-arm
    VERSION 0.1.0
    DESCRIPTION "Hakoniwa robot-arm simulator and executable recipes"
    LANGUAGES C CXX
)

set(_hako_default_robot_runtime_root
    "${CMAKE_CURRENT_SOURCE_DIR}/../hakoniwa-robot-runtime")
if(DEFINED ENV{HAKONIWA_ROBOT_RUNTIME_ROOT} AND
   NOT "$ENV{HAKONIWA_ROBOT_RUNTIME_ROOT}" STREQUAL "")
    set(_hako_default_robot_runtime_root
        "$ENV{HAKONIWA_ROBOT_RUNTIME_ROOT}")
endif()
set(HAKONIWA_ROBOT_RUNTIME_ROOT
    "${_hako_default_robot_runtime_root}" CACHE PATH
    "Sibling checkout of hakoniwa-robot-runtime")

get_filename_component(HAKO_ROBOT_RUNTIME_SOURCE_DIR
    "${HAKONIWA_ROBOT_RUNTIME_ROOT}" ABSOLUTE)
set(HAKO_ROBOT_RUNTIME_INCLUDE_DIR
    "${HAKO_ROBOT_RUNTIME_SOURCE_DIR}/include")
set(HAKO_ROBOT_RUNTIME_SRC_DIR
    "${HAKO_ROBOT_RUNTIME_SOURCE_DIR}/src")

if(NOT EXISTS "${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/actuator_runtime.cpp")
    message(FATAL_ERROR
        "hakoniwa-robot-runtime sibling checkout was not found:\n"
        "  ${HAKO_ROBOT_RUNTIME_SOURCE_DIR}\n"
        "Clone it next to this repository or set "
        "HAKONIWA_ROBOT_RUNTIME_ROOT.")
endif()
if(NOT EXISTS
   "${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}/hakoniwa/robot_runtime/runner/runner.hpp")
    message(FATAL_ERROR
        "hakoniwa-robot-runtime public include layout is not prepared:\n"
        "  ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}/hakoniwa/robot_runtime\n"
        "Expected the runtime public headers under "
        "include/hakoniwa/robot_runtime.")
endif()
message(STATUS
    "Hakoniwa robot runtime root: ${HAKO_ROBOT_RUNTIME_SOURCE_DIR}")

add_library(hako-robot-arm-runtime STATIC
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/actuator_runtime.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/source/scalar_pdu_command_source.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/source/joint_trajectory_command_source.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/source/joy_command_source.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/scalar_pdu_command_controller.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/joint_trajectory_controller.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/manual_controller.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/hold_controller.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/arbiter/priority_command_arbiter.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/joint_state_publisher.cpp
)
target_compile_features(hako-robot-arm-runtime PUBLIC cxx_std_20)
target_include_directories(hako-robot-arm-runtime PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
    $<BUILD_INTERFACE:${HAKO_ROBOT_RUNTIME_SRC_DIR}>
)

set(_hako_default_mujoco_robots_root
    "${CMAKE_CURRENT_SOURCE_DIR}/../hakoniwa-mujoco-robots")
if(DEFINED ENV{HAKONIWA_MUJOCO_ROBOTS_ROOT} AND
   NOT "$ENV{HAKONIWA_MUJOCO_ROBOTS_ROOT}" STREQUAL "")
    set(_hako_default_mujoco_robots_root
        "$ENV{HAKONIWA_MUJOCO_ROBOTS_ROOT}")
endif()
set(HAKONIWA_MUJOCO_ROBOTS_ROOT
    "${_hako_default_mujoco_robots_root}" CACHE PATH
    "Sibling checkout of hakoniwa-mujoco-robots")

set(_hako_default_foundation_prefix
    "${CMAKE_CURRENT_SOURCE_DIR}/work/foundation/install")
if(DEFINED ENV{HAKONIWA_HOME} AND
   NOT "$ENV{HAKONIWA_HOME}" STREQUAL "")
    set(_hako_default_foundation_prefix "$ENV{HAKONIWA_HOME}")
endif()
if(DEFINED ENV{HAKONIWA_FOUNDATION_PREFIX} AND
   NOT "$ENV{HAKONIWA_FOUNDATION_PREFIX}" STREQUAL "")
    set(_hako_default_foundation_prefix "$ENV{HAKONIWA_FOUNDATION_PREFIX}")
endif()
set(HAKONIWA_FOUNDATION_PREFIX
    "${_hako_default_foundation_prefix}" CACHE PATH
    "Hakoniwa Foundation install prefix")

get_filename_component(HAKO_MUJOCO_ROBOTS_SOURCE_DIR
    "${HAKONIWA_MUJOCO_ROBOTS_ROOT}" ABSOLUTE)
set(HAKO_MUJOCO_ROBOTS_CMAKE_SOURCE_DIR
    "${HAKO_MUJOCO_ROBOTS_SOURCE_DIR}/src")
set(HAKO_MUJOCO_ROBOTS_BINARY_DIR
    "${CMAKE_CURRENT_BINARY_DIR}/hakoniwa-mujoco-robots")

if(NOT EXISTS "${HAKO_MUJOCO_ROBOTS_CMAKE_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR
        "hakoniwa-mujoco-robots sibling checkout was not found:\n"
        "  ${HAKO_MUJOCO_ROBOTS_SOURCE_DIR}\n"
        "Clone it next to this repository or set "
        "HAKONIWA_MUJOCO_ROBOTS_ROOT.")
endif()

if(NOT EXISTS "${HAKONIWA_FOUNDATION_PREFIX}/include")
    message(FATAL_ERROR
        "Hakoniwa Foundation is not prepared:\n"
        "  ${HAKONIWA_FOUNDATION_PREFIX}\n"
        "Run $HAKONIWA_COMPOSER/tools/foundation.py build for the runtime recipe first, or set "
        "HAKONIWA_FOUNDATION_PREFIX.")
endif()

find_package(hakoniwa-core CONFIG REQUIRED
    PATHS "${HAKONIWA_FOUNDATION_PREFIX}"
    NO_DEFAULT_PATH)

# Public robot libraries are consumed from sibling checkouts. Core and PDU
# Endpoint are always consumed from the Foundation installation.
set(HAKO_USE_THIRDPARTY_HAKONIWA OFF CACHE BOOL
    "Build against Hakoniwa Foundation" FORCE)
set(HAKONIWA_INSTALL_PREFIX "${HAKONIWA_FOUNDATION_PREFIX}" CACHE PATH "" FORCE)
set(HAKONIWA_PDU_ENDPOINT_PREFIX "${HAKONIWA_FOUNDATION_PREFIX}" CACHE PATH "" FORCE)
set(HAKONIWA_EXTRA_PREFIX_PATH "${HAKONIWA_FOUNDATION_PREFIX}" CACHE STRING "" FORCE)
option(HAKO_ARM_ENABLE_VIEWER "Compile the MuJoCo viewer into the Arm Runtime" ON)
set(USE_VIEWER ${HAKO_ARM_ENABLE_VIEWER} CACHE BOOL "Enable the MuJoCo viewer" FORCE)
set(HAKO_BUILD_SENSOR_TESTS OFF CACHE BOOL "Build sensor tests" FORCE)
set(HAKO_BUILD_CAMERA_SMOKE_TESTS OFF CACHE BOOL "Build camera smoke tests" FORCE)

add_subdirectory(
    "${HAKO_MUJOCO_ROBOTS_CMAKE_SOURCE_DIR}"
    "${HAKO_MUJOCO_ROBOTS_BINARY_DIR}"
    EXCLUDE_FROM_ALL
)

# hakoniwa-mujoco-robots currently exposes reusable CMake targets, while a few
# dependency paths remain directory variables. Import those values from the
# processed subdirectory so delivery applications can consume the public project as
# a library without copying its implementation.
function(hako_import_mujoco_robots_variable output_variable source_variable)
    get_directory_property(
        imported_value
        DIRECTORY "${HAKO_MUJOCO_ROBOTS_CMAKE_SOURCE_DIR}"
        DEFINITION "${source_variable}"
    )
    if(NOT imported_value)
        message(FATAL_ERROR
            "Failed to import ${source_variable} from hakoniwa-mujoco-robots")
    endif()
    set(${output_variable} "${imported_value}" PARENT_SCOPE)
endfunction()

hako_import_mujoco_robots_variable(
    HAKO_MUJOCO_ROBOTS_PROJECT_ROOT PROJECT_ROOT_DIR)
hako_import_mujoco_robots_variable(
    HAKO_MUJOCO_SOURCE_DIR MUJOCO_SOURCE_DIR)
hako_import_mujoco_robots_variable(
    HAKO_MUJOCO_LIB_DIR MUJOCO_LIB_DIR)
hako_import_mujoco_robots_variable(
    HAKO_LIBMUJOCO LIBMUJOCO)
hako_import_mujoco_robots_variable(
    HAKO_CORE_INCLUDE_BASE_IMPORTED HAKO_CORE_INCLUDE_BASE)
hako_import_mujoco_robots_variable(
    HAKO_CORE_INCLUDE_ROOT_IMPORTED HAKO_CORE_INCLUDE_ROOT)
hako_import_mujoco_robots_variable(
    HAKO_PDU_TYPES_INCLUDE_DIR_IMPORTED HAKO_PDU_TYPES_INCLUDE_DIR)

set(HAKO_ASSETS_LINK_TARGET_IMPORTED hakoniwa-core::assets)
set(HAKO_CONDUCTOR_LINK_TARGET_IMPORTED hakoniwa-core::conductor)
find_library(HAKO_PDU_ENDPOINT_LINK_TARGET_IMPORTED
    NAMES hakoniwa_pdu_endpoint
    PATHS "${HAKONIWA_FOUNDATION_PREFIX}/lib"
    REQUIRED NO_DEFAULT_PATH)

add_library(hako-robot-arm-mujoco-adapter STATIC
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/physics/mujoco/mujoco_actuator_plant.cpp
)
target_compile_features(hako-robot-arm-mujoco-adapter PUBLIC cxx_std_20)
target_include_directories(hako-robot-arm-mujoco-adapter PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
)
target_include_directories(hako-robot-arm-mujoco-adapter PRIVATE
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/src
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/include
)
target_include_directories(hako-robot-arm-mujoco-adapter SYSTEM PRIVATE
    ${HAKO_MUJOCO_SOURCE_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include
)
if(HAKO_MUJOCO_LIB_DIR)
    target_link_directories(hako-robot-arm-mujoco-adapter PRIVATE
        ${HAKO_MUJOCO_LIB_DIR})
endif()
target_link_libraries(hako-robot-arm-mujoco-adapter PUBLIC
    hako-robot-arm-runtime
    ${HAKO_LIBMUJOCO}
)

add_library(hako-robot-arm-endpoint-adapter STATIC
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/float64_pdu_event_reader.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/joint_state_pdu_writer.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/joint_trajectory_pdu_event_reader.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/joy_pdu_event_reader.cpp
)
target_compile_features(hako-robot-arm-endpoint-adapter PUBLIC cxx_std_20)
target_include_directories(hako-robot-arm-endpoint-adapter PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
    ${HAKONIWA_FOUNDATION_PREFIX}/include/hakoniwa
)
target_include_directories(hako-robot-arm-endpoint-adapter PRIVATE
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/include
    ${HAKONIWA_FOUNDATION_PREFIX}/include
    ${HAKO_PDU_TYPES_INCLUDE_DIR_IMPORTED}
)
target_include_directories(hako-robot-arm-endpoint-adapter SYSTEM PRIVATE
    ${HAKO_MUJOCO_SOURCE_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include
)
target_link_libraries(hako-robot-arm-endpoint-adapter PUBLIC
    hako-robot-arm-runtime
)
target_link_libraries(hako-robot-arm-endpoint-adapter PRIVATE
    ${HAKO_ASSETS_LINK_TARGET_IMPORTED}
    ${HAKO_PDU_ENDPOINT_LINK_TARGET_IMPORTED}
)

add_library(hako-robot-arm-hakoniwa-runner STATIC
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runner/runner_factory.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runner/hakoniwa/hakoniwa_asset_driver.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runner/hakoniwa/hakoniwa_runner.cpp
)
target_compile_features(hako-robot-arm-hakoniwa-runner PUBLIC cxx_std_20)
target_include_directories(hako-robot-arm-hakoniwa-runner PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
)
target_include_directories(hako-robot-arm-hakoniwa-runner PRIVATE
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}
    ${HAKONIWA_FOUNDATION_PREFIX}/include
    ${HAKONIWA_FOUNDATION_PREFIX}/include/hakoniwa
)
target_include_directories(hako-robot-arm-hakoniwa-runner SYSTEM PRIVATE
    ${HAKO_MUJOCO_SOURCE_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include
)
target_link_libraries(hako-robot-arm-hakoniwa-runner PUBLIC
    hako-robot-arm-runtime
    hako-robot-arm-mujoco-adapter
)
target_link_libraries(hako-robot-arm-hakoniwa-runner PRIVATE
    ${HAKO_ASSETS_LINK_TARGET_IMPORTED}
    ${HAKO_CONDUCTOR_LINK_TARGET_IMPORTED}
    ${HAKO_PDU_ENDPOINT_LINK_TARGET_IMPORTED}
)

add_library(hako-robot-arm-manifest-factory STATIC
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/factory/manifest_factory.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/factory/manifest_factory_manifest.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_manifest.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_actuator.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_trajectory.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_manual.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_state_output.cpp
)
target_compile_features(hako-robot-arm-manifest-factory PUBLIC cxx_std_20)
target_include_directories(hako-robot-arm-manifest-factory PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
)
target_include_directories(hako-robot-arm-manifest-factory PRIVATE
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}
    ${HAKONIWA_FOUNDATION_PREFIX}/include
)
target_include_directories(hako-robot-arm-manifest-factory SYSTEM PRIVATE
    ${HAKO_MUJOCO_SOURCE_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include
)
target_link_libraries(hako-robot-arm-manifest-factory PUBLIC
    hako-robot-arm-hakoniwa-runner
    hako-robot-arm-endpoint-adapter
    hako-robot-arm-mujoco-adapter
    hako-robot-arm-runtime
)
target_link_libraries(hako-robot-arm-manifest-factory PRIVATE
    ${HAKO_PDU_ENDPOINT_LINK_TARGET_IMPORTED}
)

# Product entry points live under apps; reusable runtime implementation comes
# from the configured hakoniwa-robot-runtime checkout.
add_subdirectory(
    apps
    "${CMAKE_CURRENT_BINARY_DIR}/robot-arm-apps"
)
