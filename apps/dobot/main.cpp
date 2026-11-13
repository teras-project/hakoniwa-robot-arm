#include "backend.hpp"
#include "manifest_runtime_app.hpp"
#include "hakoniwa/pdu/endpoint.hpp"
#include <iostream>
#include <map>

int main(int argc, char** argv) {
    std::map<std::string, std::string> options;
    bool viewer = true;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (key == "--no-viewer") { viewer = false; continue; }
        if (i + 1 >= argc || (key != "--manifest" && key != "--service-config"
            && key != "--rpc-endpoint" && key != "--node-id")) {
            std::cerr << "Usage: robot-arm-dobot-asset --manifest FILE --service-config FILE --rpc-endpoint FILE [--node-id NAME] [--no-viewer]\n";
            return 2;
        }
        options[key] = argv[++i];
    }
    for (const auto* key : {"--manifest", "--service-config", "--rpc-endpoint"}) {
        if (options[key].empty()) { std::cerr << "Missing " << key << '\n'; return 2; }
    }
    using namespace hakoniwa::dobot;
    ::hakoniwa::robot_arm::apps::common::ManifestRuntimeAppConfig config;
    config.endpoint_name = "dobot_runtime_endpoint";
    config.viewer_enabled = viewer;
    config.realtime_sync_cycle_msec = 1; // Match wall-time-driven official clients approximately.
    config.configure_runtime = [options](rt::RuntimeExtensions& extensions,
                                          ::hakoniwa::pdu::Endpoint&) {
        auto model = std::make_shared<ServoModel>();
        auto channel = std::make_shared<DobotRpcChannel>(options.at("--service-config"),
            options.at("--rpc-endpoint"), options.contains("--node-id") ? options.at("--node-id") : "dobot_virtual");
        for (int i = 1; i <= 6; ++i)
            extensions.replaced_control_components.insert("joint" + std::to_string(i));
        extensions.replaced_control_components.insert("manual_controller");
        extensions.replaced_control_components.insert("trajectory_controller");
        extensions.sources.push_back(std::make_shared<DobotRpcSource>(channel));
        extensions.controllers.push_back(std::make_shared<ServoController>(model, channel));
        extensions.priorities.push_back({"dobot-servo", 0, {}});
        extensions.request_publishers.push_back(std::make_shared<DobotRpcPublisher>(model, channel));
    };
    return ::hakoniwa::robot_arm::apps::common::run_manifest_runtime_app(options["--manifest"], config);
}
