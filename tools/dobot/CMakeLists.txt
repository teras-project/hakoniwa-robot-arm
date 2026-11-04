cmake_minimum_required(VERSION 3.21)
project(hakoniwa_dobot_native_test LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(hakoniwa_pdu_rpc CONFIG REQUIRED)
find_package(Threads REQUIRED)
set(HAKONIWA_ROBOT_RUNTIME_ROOT "" CACHE PATH "Runtime source checkout")
set(HAKO_DOBOT_PDU_DIR "" CACHE PATH "Generated Dobot type overlay")
set(MUJOCO_ROOT "" CACHE PATH "MuJoCo Python wheel directory (contains include/ and libmujoco)")
file(GLOB MUJOCO_LIBS "${MUJOCO_ROOT}/libmujoco.so*" "${MUJOCO_ROOT}/libmujoco*.dylib")
if(NOT MUJOCO_LIBS)
  message(FATAL_ERROR "Set MUJOCO_ROOT to the installed MuJoCo Python package directory")
endif()
list(GET MUJOCO_LIBS 0 MUJOCO_LIBRARY)
add_executable(dobot-native-smoke native_smoke.cpp)
if(APPLE)
  # The Python wheel's dylib retains a framework install name that the wheel does not ship.
  get_filename_component(MUJOCO_LIBRARY_NAME "${MUJOCO_LIBRARY}" NAME)
  add_custom_command(TARGET dobot-native-smoke POST_BUILD
    COMMAND ${CMAKE_INSTALL_NAME_TOOL} -change
      "@rpath/mujoco.framework/Versions/A/${MUJOCO_LIBRARY_NAME}"
      "${MUJOCO_LIBRARY}" "$<TARGET_FILE:dobot-native-smoke>")
endif()
target_include_directories(dobot-native-smoke PRIVATE ../../apps/dobot
  "${HAKONIWA_ROBOT_RUNTIME_ROOT}/include" "${HAKONIWA_ROBOT_RUNTIME_ROOT}/src"
  "${HAKO_DOBOT_PDU_DIR}/pdu/types" "${MUJOCO_ROOT}/include")
target_link_libraries(dobot-native-smoke PRIVATE hakoniwa_pdu_rpc::rpc Threads::Threads "${MUJOCO_LIBRARY}")
add_executable(dobot-servo-test test/servo_model_test.cpp)
target_include_directories(dobot-servo-test PRIVATE ../../apps/dobot)
enable_testing()
add_test(NAME servo-model COMMAND dobot-servo-test)
