#include "manifest_runtime_app.hpp"

#include "mujoco_viewer.hpp"

#include "hakoniwa/robot_runtime/factory/manifest_factory.hpp"

#include <exception>
#include <iostream>
#include <memory>

namespace hakoniwa::robot_arm::apps::common {
namespace {

void print_viewer_help()
{
    std::cout
        << "\nControls:\n"
        << "  p      : pause / resume simulation\n"
        << "  r      : reset simulation state\n"
        << "  h      : show this help\n"
        << "  q / Esc: stop the asset and close the viewer\n\n"
        << "Commands and state outputs are configured by the manifest.\n"
        << std::endl;
}

} // namespace

int run_manifest_runtime_app(
    const std::string& manifest_path,
    const ManifestRuntimeAppConfig& config)
{
    std::unique_ptr<::hakoniwa::robot_runtime::runner::IRunner> runtime_runner;
    try {
        runtime_runner =
            ::hakoniwa::robot_runtime::factory::ManifestFactory::create(
                manifest_path,
                {
                    config.asset_name,
                    config.endpoint_name,
                    config.realtime_sync_cycle_msec,
                });
    } catch (const std::exception& error) {
        std::cerr << "[ERROR] Failed to create Runtime from manifest: "
                  << error.what() << std::endl;
        return 1;
    }

    if (runtime_runner->start() != 0) {
        return 1;
    }

    bool viewer_failed = false;
    if (config.viewer_enabled) {
        print_viewer_help();
        try {
            run_mujoco_viewer(
                runtime_runner->model(),
                runtime_runner->data(),
                runtime_runner->running(),
                runtime_runner->model_mutex(),
                {
                    [&runtime_runner]() { runtime_runner->request_stop(); },
                    [&runtime_runner]() { runtime_runner->toggle_pause(); },
                    [&runtime_runner]() { runtime_runner->request_reset(); },
                    []() { print_viewer_help(); },
                });
        } catch (const std::exception& error) {
            std::cerr << "[ERROR] Viewer failed: "
                      << error.what() << std::endl;
            viewer_failed = true;
        }
        runtime_runner->request_stop();
    }

    const int runner_result = runtime_runner->wait();
    return runner_result == 0 && !viewer_failed ? 0 : 1;
}

} // namespace hakoniwa::robot_arm::apps::common
