#pragma once

#include <cstdint>
#include <functional>
#include "runtime/runtime_factory.hpp"
namespace hakoniwa::pdu { class Endpoint; }
#include <string>

namespace hakoniwa::robot_arm::apps::common {

struct ManifestRuntimeAppConfig {
    std::string asset_name;
    std::string endpoint_name;
    bool viewer_enabled {true};
    std::uint64_t realtime_sync_cycle_msec {0};
    std::function<void(
        ::hakoniwa::robot_runtime::runtime::RuntimeExtensions&,
        ::hakoniwa::pdu::Endpoint&)> configure_runtime;
};

[[nodiscard]] int run_manifest_runtime_app(
    const std::string& manifest_path,
    const ManifestRuntimeAppConfig& config);

} // namespace hakoniwa::robot_arm::apps::common
