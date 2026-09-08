add_executable(robot-arm-hakoniwa-asset
    robot-arm/robot-arm-hakoniwa-asset.cpp
    common/manifest_runtime_app.cpp
    common/mujoco_viewer.cpp
    common/robot_arm_app.cpp
)

set_target_properties(robot-arm-hakoniwa-asset PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
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

target_link_libraries(robot-arm-hakoniwa-asset PRIVATE
    hako-robot-arm-manifest-factory
    mujoco-common
    ${HAKO_LIBMUJOCO}
)

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
