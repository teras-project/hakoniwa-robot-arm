if(DEFINED ENV{HAKO_ARM_BUILD_EXCAVATOR} AND
   NOT "$ENV{HAKO_ARM_BUILD_EXCAVATOR}" STREQUAL "")
    set(HAKO_ARM_BUILD_EXCAVATOR
        "$ENV{HAKO_ARM_BUILD_EXCAVATOR}" CACHE BOOL
        "Build the excavator application" FORCE)
else()
    option(HAKO_ARM_BUILD_EXCAVATOR
        "Build the excavator application" ON)
endif()

add_executable(robot-arm-hakoniwa-asset
    robot-arm/robot-arm-hakoniwa-asset.cpp
    common/manifest_runtime_app.cpp
    common/mujoco_viewer.cpp
    common/robot_arm_app.cpp
)

set_target_properties(robot-arm-hakoniwa-asset PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)

target_compile_features(robot-arm-hakoniwa-asset PRIVATE cxx_std_20)

target_compile_definitions(robot-arm-hakoniwa-asset PRIVATE
    HAKO_ARM_ENABLE_VIEWER=$<BOOL:${HAKO_ARM_ENABLE_VIEWER}>
)

target_include_directories(robot-arm-hakoniwa-asset PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/src
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/include
)

target_include_directories(robot-arm-hakoniwa-asset SYSTEM PRIVATE
    ${HAKO_MUJOCO_SOURCE_DIR}
    ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include
)

if(HAKO_MUJOCO_LIB_DIR)
    target_link_directories(robot-arm-hakoniwa-asset PRIVATE ${HAKO_MUJOCO_LIB_DIR})
endif()

if(HAKO_ARM_BUILD_EXCAVATOR)
    add_executable(robot-excavator-hakoniwa-asset
        excavator/robot-excavator-hakoniwa-asset.cpp
        ${PROJECT_SOURCE_DIR}/src/controllers/excavator_controller.cpp
        ${PROJECT_SOURCE_DIR}/src/controllers/excavator_mobile_base.cpp
        ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/src/config/asset_manifest.cpp
    )
    set_target_properties(robot-excavator-hakoniwa-asset PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
    )
    target_compile_features(robot-excavator-hakoniwa-asset PRIVATE cxx_std_20)
    target_compile_definitions(robot-excavator-hakoniwa-asset PRIVATE
        HAKO_ARM_ENABLE_VIEWER=$<BOOL:${HAKO_ARM_ENABLE_VIEWER}>)
    target_include_directories(robot-excavator-hakoniwa-asset PRIVATE
        ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/src
        ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/include
        ${HAKO_ROBOT_RUNTIME_INCLUDE_DIR}
        ${HAKO_ROBOT_RUNTIME_SRC_DIR}
        ${PROJECT_SOURCE_DIR}/src
        ${PROJECT_SOURCE_DIR}/src/controllers
        ${HAKO_CORE_INCLUDE_BASE_IMPORTED}
        ${HAKO_CORE_INCLUDE_ROOT_IMPORTED}
        ${HAKO_PDU_TYPES_INCLUDE_DIR_IMPORTED})
    target_include_directories(robot-excavator-hakoniwa-asset SYSTEM PRIVATE
        ${HAKO_MUJOCO_SOURCE_DIR}
        ${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include)
    if(HAKO_MUJOCO_LIB_DIR)
        target_link_directories(robot-excavator-hakoniwa-asset PRIVATE ${HAKO_MUJOCO_LIB_DIR})
    endif()
    target_link_libraries(robot-excavator-hakoniwa-asset PRIVATE
        msensors mujoco-common ${HAKO_LIBMUJOCO}
        ${HAKO_ASSETS_LINK_TARGET_IMPORTED}
        ${HAKO_CONDUCTOR_LINK_TARGET_IMPORTED}
        ${HAKO_PDU_ENDPOINT_LINK_TARGET_IMPORTED})
    if(MSVC)
        target_compile_options(robot-excavator-hakoniwa-asset PRIVATE
            /W4 /external:W0 /wd4710 /wd4711 /wd5220 /wd5247)
    endif()
    if(WIN32)
        add_custom_command(TARGET robot-excavator-hakoniwa-asset POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_RUNTIME_DLLS:robot-excavator-hakoniwa-asset>
                $<TARGET_FILE_DIR:robot-excavator-hakoniwa-asset>
            COMMAND_EXPAND_LISTS)
    endif()
endif()

target_link_libraries(robot-arm-hakoniwa-asset PRIVATE
    hako-robot-arm-manifest-factory
    mujoco-common
    ${HAKO_LIBMUJOCO}
)
if(HAKO_ROBOT_ARM_ENABLE_SENSOR)
    # The generated registration is linked into the executable itself, so its
    # static initializer always runs and pulls in each implementation's entry point.
    target_sources(robot-arm-hakoniwa-asset PRIVATE
        ${HAKO_ROBOT_ARM_SENSOR_REGISTRATION_SOURCE})
    target_include_directories(robot-arm-hakoniwa-asset PRIVATE
        ${HAKO_ROBOT_RUNTIME_SRC_DIR})
    target_link_libraries(robot-arm-hakoniwa-asset PRIVATE
        ${HAKO_ROBOT_ARM_SENSOR_LIBRARIES})
endif()

if(MSVC)
    target_compile_options(robot-arm-hakoniwa-asset PRIVATE
        /W4 /external:W0 /wd4710 /wd4711 /wd5220 /wd5247
    )
endif()

if(WIN32)
    add_custom_command(TARGET robot-arm-hakoniwa-asset POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_RUNTIME_DLLS:robot-arm-hakoniwa-asset>
            $<TARGET_FILE_DIR:robot-arm-hakoniwa-asset>
        COMMAND_EXPAND_LISTS
    )
endif()

option(HAKO_ARM_ENABLE_DOBOT "Build the Dobot ROS service compatible simulation backend" OFF)
if(HAKO_ARM_ENABLE_DOBOT)
    set(HAKO_DOBOT_PDU_DIR "" CACHE PATH "Output of tools/dobot/generate_types.py")
    if(NOT EXISTS "${HAKO_DOBOT_PDU_DIR}/pdu/types/dobot_msgs_v4_msgs/pdu_cpptype_ServoJRequestPacket.hpp")
        message(FATAL_ERROR "Generate Dobot PDU types first and set HAKO_DOBOT_PDU_DIR")
    endif()
    find_package(hakoniwa_pdu_rpc CONFIG REQUIRED)
    add_executable(robot-arm-dobot-asset dobot/main.cpp common/manifest_runtime_app.cpp common/mujoco_viewer.cpp)
    target_compile_features(robot-arm-dobot-asset PRIVATE cxx_std_20)
    target_compile_definitions(robot-arm-dobot-asset PRIVATE HAKO_ARM_ENABLE_DOBOT=1 HAKO_ARM_ENABLE_VIEWER=$<BOOL:${HAKO_ARM_ENABLE_VIEWER}>)
    target_include_directories(robot-arm-dobot-asset PRIVATE
        common "${HAKO_ROBOT_RUNTIME_SRC_DIR}" "${HAKO_DOBOT_PDU_DIR}/pdu/types"
        "${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/src" "${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/include")
    target_include_directories(robot-arm-dobot-asset SYSTEM PRIVATE
        "${HAKO_MUJOCO_SOURCE_DIR}" "${HAKO_MUJOCO_ROBOTS_PROJECT_ROOT}/thirdparty/nolman/single_include")
    if(HAKO_MUJOCO_LIB_DIR)
        target_link_directories(robot-arm-dobot-asset PRIVATE ${HAKO_MUJOCO_LIB_DIR})
    endif()
    target_link_libraries(robot-arm-dobot-asset PRIVATE hako-robot-arm-manifest-factory
        mujoco-common ${HAKO_LIBMUJOCO} hakoniwa_pdu_rpc::rpc)
    set_target_properties(robot-arm-dobot-asset PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    if(WIN32)
        add_custom_command(TARGET robot-arm-dobot-asset POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_RUNTIME_DLLS:robot-arm-dobot-asset>
                $<TARGET_FILE_DIR:robot-arm-dobot-asset>
            COMMAND_EXPAND_LISTS)
    endif()
endif()
