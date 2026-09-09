#include "mujoco_viewer.hpp"

#if HAKO_ARM_ENABLE_VIEWER
#include "viewer/mujoco_viewer.hpp"
#include <GLFW/glfw3.h>
#endif

#include <stdexcept>
#include <utility>

namespace hakoniwa::robot_arm::apps::common {

void run_mujoco_viewer(
    mjModel* model,
    mjData* data,
    std::atomic_bool& running,
    std::mutex& model_mutex,
    ViewerActions actions)
{
#if HAKO_ARM_ENABLE_VIEWER
    MujocoRenderRuntime viewer(
        model, data, running, model_mutex, MujocoRenderWindowMode::Visible);
    viewer.SetKeyCallback(
        [actions = std::move(actions)](const int key, const int action, int) {
            if (action != GLFW_PRESS && action != GLFW_REPEAT) {
                return;
            }
            if (key == GLFW_KEY_ESCAPE || key == GLFW_KEY_Q) {
                actions.stop();
            } else if (key == GLFW_KEY_P) {
                actions.toggle_pause();
            } else if (key == GLFW_KEY_R) {
                actions.reset();
            } else if (key == GLFW_KEY_H) {
                actions.print_help();
            }
        });
    viewer.Run();
#else
    (void)model;
    (void)data;
    (void)running;
    (void)model_mutex;
    (void)actions;
    throw std::runtime_error("Viewer support is not compiled in");
#endif
}

} // namespace hakoniwa::robot_arm::apps::common
