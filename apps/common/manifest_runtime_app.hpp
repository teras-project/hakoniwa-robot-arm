#pragma once

#include <cstdint>
#include <functional>
namespace hakoniwa::robot_runtime::runner { struct HakoniwaRunnerResources; }
#include <string>

namespace hakoniwa::robot_arm::apps::common {

struct ManifestRuntimeAppConfig {
    std::string asset_name;
    std::string endpoint_name;
    bool viewer_enabled {true};
    std::uint64_t realtime_sync_cycle_msec {0};
    std::function<void(::hakoniwa::robot_runtime::runner::HakoniwaRunnerResources&)> configure_resources;
};

[[nodiscard]] int run_manifest_runtime_app(
    const std::string& manifest_path,
    const ManifestRuntimeAppConfig& config);

} // namespace hakoniwa::robot_arm::apps::common
