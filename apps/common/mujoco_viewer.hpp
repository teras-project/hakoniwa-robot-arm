#pragma once

#include <atomic>
#include <functional>
#include <mutex>

struct mjData_;
struct mjModel_;
using mjData = mjData_;
using mjModel = mjModel_;

namespace hakoniwa::robot_arm::apps::common {

struct ViewerActions {
    std::function<void()> stop;
    std::function<void()> toggle_pause;
    std::function<void()> reset;
    std::function<void()> print_help;
    /// Optional: called on each viewer pass outside the viewer's MuJoCo mutex
    /// (serves camera render requests on the main thread).
    std::function<void()> idle;
};

/** Runs the optional desktop viewer against externally owned MuJoCo state. */
void run_mujoco_viewer(
    mjModel* model,
    mjData* data,
    std::atomic_bool& running,
    std::mutex& model_mutex,
    ViewerActions actions);

} // namespace hakoniwa::robot_arm::apps::common
