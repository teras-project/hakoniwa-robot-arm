#include "manifest_runtime_app.hpp"

#include "mujoco_viewer.hpp"
#if defined(HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR) && HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR
// Camera sensors draw on the main thread through the render server.
#include "physics/render_server.hpp"
#endif

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
#if defined(HAKO_ARM_ENABLE_DOBOT) && HAKO_ARM_ENABLE_DOBOT
        ::hakoniwa::robot_runtime::factory::ManifestFactoryConfig factory_config;
        factory_config.asset_name = config.asset_name;
        factory_config.endpoint_name = config.endpoint_name;
        factory_config.realtime_sync_cycle_msec = config.realtime_sync_cycle_msec;
        factory_config.configure_runtime = config.configure_runtime;
        runtime_runner =
            ::hakoniwa::robot_runtime::factory::ManifestFactory::create(
                manifest_path,
                std::move(factory_config));
#else
        runtime_runner = ::hakoniwa::robot_runtime::factory::ManifestFactory::create(
            manifest_path, {config.asset_name, config.endpoint_name, config.realtime_sync_cycle_msec});
#endif
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
            // The viewer draws the Runner's copy of the world under its own lock:
            // it never waits for a step, which may wait for this thread to render.
            run_mujoco_viewer(
                runtime_runner->model(),
                runtime_runner->view_data(),
                runtime_runner->running(),
                runtime_runner->view_mutex(),
                {
                    [&runtime_runner]() { runtime_runner->request_stop(); },
                    [&runtime_runner]() { runtime_runner->toggle_pause(); },
                    [&runtime_runner]() { runtime_runner->request_reset(); },
                    []() { print_viewer_help(); },
#if defined(HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR) && HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR
                    []() { hako::robots::physics::impl::RenderServer::instance().process_pending(); },
#else
                    {},
#endif
                });
        } catch (const std::exception& error) {
            std::cerr << "[ERROR] Viewer failed: "
                      << error.what() << std::endl;
            viewer_failed = true;
        }
        runtime_runner->request_stop();
    }
#if defined(HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR) && HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR
    else {
        // No viewer: the main thread serves camera render requests until the
        // runner stops. Without cameras it only waits.
        hako::robots::physics::impl::RenderServer::instance().run(runtime_runner->running());
    }
    // A step still waiting for an image must not wait forever once nobody serves.
    hako::robots::physics::impl::RenderServer::instance().shutdown();
#endif

    const int runner_result = runtime_runner->wait();
#if defined(HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR) && HAKONIWA_ROBOT_RUNTIME_ENABLE_SENSOR
    // Graphics resources are freed on the thread that made them.
    hako::robots::physics::impl::RenderServer::instance().release_drawers();
#endif
    return runner_result == 0 && !viewer_failed ? 0 : 1;
}

} // namespace hakoniwa::robot_arm::apps::common
