#include "backend.hpp"
#include "manifest_runtime_app.hpp"
#include "runner/hakoniwa/hakoniwa_runner.hpp"
#include "runtime/arbiter/priority_command_arbiter.hpp"
#include "runtime/publisher/joint_state_publisher.hpp"
#include "hakoniwa/robot_runtime/adapters/endpoint/joint_state_pdu_writer.hpp"
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
    using Resources = ::hakoniwa::robot_runtime::runner::HakoniwaRunnerResources;
    ::hakoniwa::robot_arm::apps::common::ManifestRuntimeAppConfig config;
    config.endpoint_name = "dobot_runtime_endpoint";
    config.viewer_enabled = viewer;
    config.realtime_sync_cycle_msec = 1; // Match wall-time-driven official clients approximately.
    config.configure_resources = [options](Resources& resources) {
        auto model = std::make_shared<ServoModel>();
        auto controller = std::make_shared<ServoController>(model);
        auto boundary = std::make_shared<RpcBoundary>(model, options.at("--service-config"),
            options.at("--rpc-endpoint"), options.contains("--node-id") ? options.at("--node-id") : "dobot_virtual");
        std::vector<rt::JointStateOutputBinding> joints;
        for (int i = 1; i <= 6; ++i) joints.push_back({"joint" + std::to_string(i), "joint" + std::to_string(i)});
        auto writer = std::make_shared<::hakoniwa::robot_runtime::adapters::hakoniwa::JointStatePduWriter>(
            *resources.endpoint, "Nova5", "joint_states");
        auto joint_states = std::make_shared<rt::JointStatePublisher>("dobot_joint_states", joints, 50., writer);
        auto arbiter = std::make_shared<rt::PriorityCommandArbiter>(
            std::vector<rt::ControllerPriority>{{"dobot-servo", 0, {}}});
        resources.runtime = std::make_unique<rt::ActuatorRuntime>(
            std::vector<std::shared_ptr<rt::ICommandSource>>{},
            std::vector<std::shared_ptr<rt::IController>>{controller}, arbiter, resources.plant,
            std::vector<std::shared_ptr<rt::IStatePublisher>>{boundary, joint_states});
    };
    return ::hakoniwa::robot_arm::apps::common::run_manifest_runtime_app(options["--manifest"], config);
}
