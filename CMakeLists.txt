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
    # The Runtime's mobile-base switch (as Urban): MultiDOF body-state outputs
    # (an object's pose, e.g. for a viewer) and the Ackermann parts it brings.
    # A manifest without those components runs as before.
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/multi_dof_joint_state_publisher.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/source/ackermann_drive_command_source.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/ackermann_controller.cpp
)
target_compile_features(hako-robot-arm-runtime PUBLIC cxx_std_20)
target_compile_definitions(hako-robot-arm-runtime PUBLIC HAKONIWA_ROBOT_RUNTIME_ENABLE_MOBILE_BASE=1)
target_include_directories(hako-robot-arm-runtime PUBLIC
    ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
    $<BUILD_INTERFACE:${HAKO_ROBOT_RUNTIME_SRC_DIR}>
)

# Controller plugins are opt-in: a manifest component {"kind": "controller",
# "type": "plugin"} loads a shared library through the Runtime's C plugin
# interface (include/hakoniwa/robot_runtime/plugin/controller_plugin.h). Off,
# such a component is refused with a message.
option(HAKO_ROBOT_ARM_CONTROLLER_PLUGIN "Build the Runtime controller plugin loader" OFF)
if(HAKO_ROBOT_ARM_CONTROLLER_PLUGIN)
    target_sources(hako-robot-arm-runtime PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/plugin/plugin_library.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/controller/plugin_controller.cpp
    )
    # PUBLIC: the switch changes RuntimeDefinition, so every library that
    # sees it must be compiled with the same value.
    target_compile_definitions(hako-robot-arm-runtime PUBLIC
        HAKONIWA_ROBOT_RUNTIME_ENABLE_CONTROLLER_PLUGIN=1)
    target_link_libraries(hako-robot-arm-runtime PUBLIC ${CMAKE_DL_LIBS})
endif()

# Sensors are opt-in. An application that uses them enables the switch, lists
# the sensor implementations it links by name and gives their libraries. The
# registration of each implementation is generated from its name
# (hakoniwa-sensor-adapter sensor_adapter_implementation.hpp); the Runtime
# itself links no implementation.
option(HAKO_ROBOT_ARM_ENABLE_SENSOR "Build the Runtime sensor stage" OFF)
set(HAKO_ROBOT_ARM_SENSOR_ADAPTER_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../hakoniwa-sensor-adapter" CACHE PATH
    "Checkout of hakoniwa-sensor-adapter (header-only interfaces)")
set(HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS "" CACHE STRING
    "Names of the linked sensor implementations, for example hakoniwa;gazebo")
set(HAKO_ROBOT_ARM_SENSOR_LIBRARIES "" CACHE STRING
    "Libraries of the listed sensor implementations")
if(HAKO_ROBOT_ARM_ENABLE_SENSOR)
    if(NOT EXISTS "${HAKO_ROBOT_ARM_SENSOR_ADAPTER_ROOT}/include/hakoniwa/sensor_adapter/sensor_adapter_implementation.hpp")
        message(FATAL_ERROR "hakoniwa-sensor-adapter with sensor_adapter_implementation.hpp not found: "
            "${HAKO_ROBOT_ARM_SENSOR_ADAPTER_ROOT}")
    endif()
    if(HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS STREQUAL "")
        message(FATAL_ERROR "HAKO_ROBOT_ARM_ENABLE_SENSOR needs at least one sensor implementation"
            " (HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS)")
    endif()
    set(_hako_sensor_declarations "")
    set(_hako_sensor_registrations "")
    foreach(_hako_sensor_name IN LISTS HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS)
        if(NOT _hako_sensor_name MATCHES "^[A-Za-z_][A-Za-z0-9_]*$")
            message(FATAL_ERROR "sensor implementation name is not a C identifier: ${_hako_sensor_name}")
        endif()
        string(APPEND _hako_sensor_declarations
            "HAKO_SENSOR_ADAPTER_DECLARE_IMPLEMENTATION(${_hako_sensor_name});\n")
        string(APPEND _hako_sensor_registrations
            "    add(HAKO_SENSOR_ADAPTER_IMPLEMENTATION_ENTRY(${_hako_sensor_name})());\n")
    endforeach()
    set(HAKO_ROBOT_ARM_SENSOR_REGISTRATION_SOURCE
        "${CMAKE_CURRENT_BINARY_DIR}/generated/sensor_implementations.cpp")
    file(WRITE "${HAKO_ROBOT_ARM_SENSOR_REGISTRATION_SOURCE}.in"
"// Generated by CMake from HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS. Do not edit.
#include \"runtime/sensor/sensor_registry.hpp\"

#include <cstdlib>
#include <iostream>
#include <string>

${_hako_sensor_declarations}
namespace {
void add(const ::hakoniwa::sensor_adapter::SensorAdapterImplementation* implementation)
{
    std::string error;
    if (!::hakoniwa::robot_runtime::runtime::sensor::sensor_implementation_registry().add(
            implementation, &error)) {
        std::cerr << \"[ERROR] \" << error << std::endl;
        std::abort();
    }
}
const bool registered = [] {
${_hako_sensor_registrations}    return true;
}();
} // namespace
")
    configure_file("${HAKO_ROBOT_ARM_SENSOR_REGISTRATION_SOURCE}.in"
        "${HAKO_ROBOT_ARM_SENSOR_REGISTRATION_SOURCE}" COPYONLY)
    target_sources(hako-robot-arm-runtime PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/sensor/sensor_registry.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_joint_state_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_wrench_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_imu_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_laser_scan_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_point_cloud_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_range_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_depth_image_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_compressed_image_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_magnetic_field_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_fluid_pressure_publisher.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/publisher/sensor_nav_sat_fix_publisher.cpp
    )
    # hakoniwa-sensor-adapter's reference implementation (the true values) is built
    # from source; the other implementations come as HAKO_ROBOT_ARM_SENSOR_LIBRARIES.
    if("reference" IN_LIST HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS)
        set(_hako_sensor_reference_source
            "${HAKO_ROBOT_ARM_SENSOR_ADAPTER_ROOT}/src/reference/reference_implementation.cpp")
        if(NOT EXISTS "${_hako_sensor_reference_source}")
            message(FATAL_ERROR "the reference sensor implementation is not in this hakoniwa-sensor-adapter: "
                "${_hako_sensor_reference_source}")
        endif()
        target_sources(hako-robot-arm-runtime PRIVATE ${_hako_sensor_reference_source})
        # nlohmann/json for it: added below, once hakoniwa-mujoco-robots is imported.
    endif()
    target_compile_definitions(hako-robot-arm-runtime PUBLIC
        HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR=1
        HAKONIWA_ROBOT_RUNTIME_SENSOR_CATALOG_PATH="${HAKO_ROBOT_RUNTIME_SOURCE_DIR}/catalog/sensor-implementations.json"
    )
    target_include_directories(hako-robot-arm-runtime PUBLIC
        ${HAKO_ROBOT_ARM_SENSOR_ADAPTER_ROOT}/include)
endif()

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
if(HAKO_ROBOT_ARM_ENABLE_SENSOR AND "reference" IN_LIST HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS)
    # The reference sensor implementation reads its definitions with nlohmann/json.
    target_include_directories(hako-robot-arm-runtime PRIVATE
        ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include)
endif()
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
if(HAKO_ROBOT_ARM_ENABLE_SENSOR)
    target_sources(hako-robot-arm-mujoco-adapter PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/physics/mujoco/mujoco_sensor_stage.cpp)
    # The world's ray caster for range sensors (hakoniwa-mujoco-robots).
    target_compile_definitions(hako-robot-arm-mujoco-adapter PRIVATE
        HAKO_MUJOCO_ROBOTS_ENABLE_RAY_CASTER
        HAKO_MUJOCO_ROBOTS_ENABLE_IMAGE_RENDERER)
    # The image renderer draws with OpenGL through GLFW: the GLFW headers of the
    # viewer library (the application already links that library).
    target_include_directories(hako-robot-arm-mujoco-adapter SYSTEM PRIVATE
        $<TARGET_PROPERTY:mujoco-common,INTERFACE_INCLUDE_DIRECTORIES>)
endif()
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
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/multi_dof_joint_state_pdu_writer.cpp
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/ackermann_drive_pdu_event_reader.cpp
)
if(HAKO_ROBOT_ARM_ENABLE_SENSOR)
    target_sources(hako-robot-arm-endpoint-adapter PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/wrench_stamped_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/imu_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/laser_scan_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/point_cloud2_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/range_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/depth_image_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/compressed_image_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/magnetic_field_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/fluid_pressure_pdu_writer.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/adapters/endpoint/nav_sat_fix_pdu_writer.cpp)
    # JPEG for sensor_msgs/CompressedImage (stb_image_write, vendored in the Runtime).
    target_include_directories(hako-robot-arm-endpoint-adapter SYSTEM PRIVATE
        ${HAKO_ROBOT_RUNTIME_SOURCE_DIR}/third_party)
endif()
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
    ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_ackermann.cpp
)
if(HAKO_ROBOT_ARM_CONTROLLER_PLUGIN)
    target_sources(hako-robot-arm-manifest-factory PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_plugin.cpp)
endif()
if(HAKO_ROBOT_ARM_ENABLE_SENSOR)
    target_sources(hako-robot-arm-manifest-factory PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/runtime_factory_sensor.cpp
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}/runtime/sensor/sensor_catalog.cpp)
endif()
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

include(CTest)
# Product entry points live under apps; reusable runtime implementation comes
# from the configured hakoniwa-robot-runtime checkout.
add_subdirectory(
    apps
    "${CMAKE_CURRENT_BINARY_DIR}/robot-arm-apps"
)

if(BUILD_TESTING AND HAKO_ARM_ENABLE_DOBOT)
    add_executable(test-runtime-extensions
        "${HAKO_ROBOT_RUNTIME_SRC_DIR}/../tests/test_runtime_extensions.cpp")
    target_compile_features(test-runtime-extensions PRIVATE cxx_std_20)
    target_include_directories(test-runtime-extensions PRIVATE
        "${HAKO_ROBOT_RUNTIME_SRC_DIR}")
    target_link_libraries(test-runtime-extensions PRIVATE hako-robot-arm-runtime)
    add_test(NAME runtime_extensions COMMAND test-runtime-extensions)
endif()
