#include "robot_arm_app.hpp"

#include "manifest_runtime_app.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

namespace hakoniwa::robot_arm::apps::common {
namespace {

constexpr const char* kDefaultEndpointName = "robot_arm_endpoint";

struct LaunchOptions {
    std::string manifest_path;
    std::string asset_name_override;
    std::string endpoint_name {kDefaultEndpointName};
    bool viewer_enabled {true};
    std::uint64_t realtime_sync_cycle_msec {0};
};

std::string env_or_default(const char* name, const char* fallback)
{
    const char* value = std::getenv(name);
    return value != nullptr && value[0] != '\0' ? value : fallback;
}

void print_usage(const char* program)
{
    std::cout
        << "Usage:\n"
        << "  " << program << " <asset-manifest.json>\n"
        << "  " << program
        << " --manifest <asset-manifest.json> [--no-viewer]"
           " [--realtime-sync-cycle-msec <0..>]\n\n"
        << "Options:\n"
        << "  --no-viewer    Run without a MuJoCo window.\n"
        << "  --realtime-sync-cycle-msec <0..>\n"
        << "                 Reconcile simulation and wall time at this interval.\n\n"
        << "Environment:\n"
        << "  HAKO_ROBOT_ARM_MANIFEST       Default manifest path\n"
        << "  HAKO_ROBOT_ARM_ASSET_NAME     Override manifest.name\n"
        << "  HAKO_ROBOT_ARM_ENDPOINT_NAME  Endpoint instance name\n";
}

bool parse_options(const int argc, char** argv, LaunchOptions& options)
{
    options.manifest_path = env_or_default(
        "HAKO_ROBOT_ARM_MANIFEST", "");
    options.asset_name_override = env_or_default(
        "HAKO_ROBOT_ARM_ASSET_NAME", "");
    options.endpoint_name = env_or_default(
        "HAKO_ROBOT_ARM_ENDPOINT_NAME",
        kDefaultEndpointName);
#if !HAKO_ARM_ENABLE_VIEWER
    options.viewer_enabled = false;
#endif

    bool positional_manifest_seen = false;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--help") {
            print_usage(argv[0]);
            return false;
        }
        if (argument == "--no-viewer") {
            options.viewer_enabled = false;
            continue;
        }
        if (argument == "--realtime-sync-cycle-msec") {
            if (++index >= argc || argv[index][0] == '-') {
                throw std::invalid_argument(
                    "--realtime-sync-cycle-msec expects an integer >= 0");
            }
            std::size_t parsed = 0;
            const std::string value = argv[index];
            options.realtime_sync_cycle_msec =
                std::stoull(value, &parsed);
            if (parsed != value.size()) {
                throw std::invalid_argument(
                    "--realtime-sync-cycle-msec expects an integer >= 0");
            }
            continue;
        }
        if (argument == "--manifest") {
            if (++index >= argc) {
                throw std::invalid_argument(
                    "--manifest expects a path");
            }
            options.manifest_path = argv[index];
            positional_manifest_seen = true;
            continue;
        }
        if (!argument.empty()
            && argument[0] != '-'
            && !positional_manifest_seen) {
            options.manifest_path = argument;
            positional_manifest_seen = true;
            continue;
        }
        throw std::invalid_argument(
            "unexpected command-line argument: " + argument);
    }

    if (options.manifest_path.empty()) {
        throw std::invalid_argument(
            "asset manifest path is required");
    }
    options.manifest_path =
        std::filesystem::absolute(options.manifest_path)
            .lexically_normal()
            .string();
    return true;
}

} // namespace

int run_robot_arm_app(int argc, char** argv)
{
    LaunchOptions options;
    try {
        if (!parse_options(argc, argv, options)) {
            return 0;
        }
    } catch (const std::exception& error) {
        std::cerr << "[ERROR] " << error.what() << std::endl;
        print_usage(argv[0]);
        return 1;
    }

    return run_manifest_runtime_app(
        options.manifest_path,
        {
            options.asset_name_override,
            options.endpoint_name,
            options.viewer_enabled,
            options.realtime_sync_cycle_msec,
        });
}

} // namespace hakoniwa::robot_arm::apps::common
