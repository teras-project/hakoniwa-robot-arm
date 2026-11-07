#include "config/asset_manifest.hpp"
#include "excavator_controller.hpp"
#include "excavator_mobile_base.hpp"
#include "hako_asset.h"
#include "hako_conductor.h"
#include "hakoniwa/pdu/adapter/sensor_msgs/joint_state.hpp"
#include "hakoniwa/pdu/endpoint.hpp"
#include "physics/physics_impl.hpp"
#include "runner/realtime_pacer.hpp"
#include "sensors/joint_state/joint_state_sensor.hpp"
#if HAKO_ARM_ENABLE_VIEWER
#include "viewer/mujoco_viewer.hpp"
#include <GLFW/glfw3.h>
#endif
#include <mujoco/mujoco.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>

namespace
{

constexpr const char* kDefaultEndpointName = "robot_excavator_endpoint";
constexpr const char* kHomeKeyframeName = "excavator_home";

std::shared_ptr<hako::robots::physics::impl::WorldImpl> world;
std::shared_ptr<hako::robots::actuator::IJointTrajectoryActuator>
    trajectory_actuator;
std::unique_ptr<hako::robots::sensor::JointStateSensor> joint_state_sensor;
std::unique_ptr<hako::robots::pdu::adapter::sensor_msgs::JointStatePduAdapter>
    joint_state_adapter;
std::unique_ptr<hakoniwa::pdu::Endpoint> endpoint;
std::unique_ptr<ExcavatorMobileBase> mobile_base;
std::unique_ptr<ExcavatorController> excavator_controller;

std::string manifest_path;
std::string model_path;
std::string trajectory_config_path;
std::string joint_state_config_path;
std::string pdu_def_path;
std::string endpoint_config_path;
std::string asset_name;
std::string endpoint_name;
std::string trajectory_pdu_robot;
std::string trajectory_pdu_name;
std::string joint_state_pdu_robot;
std::string joint_state_pdu_name;

std::atomic_bool running {true};
std::atomic_bool viewer_running {true};
std::atomic_bool endpoint_ready {false};
std::atomic_bool paused {false};
std::atomic_bool reset_requested {false};
std::atomic_bool print_help_requested {false};
bool viewer_enabled = true;
std::uint64_t realtime_sync_cycle_msec = 0;
std::mutex mujoco_mutex;

std::string EnvOrDefault(const char* name, const char* fallback)
{
    const char* value = std::getenv(name);
    if (value != nullptr && value[0] != '\0') {
        return value;
    }
    return fallback;
}

void PrintUsage(const char* program)
{
    std::cout
        << "Usage:\n"
        << "  " << program << "\n"
        << "  " << program << " <asset-manifest.json>\n"
        << "  " << program << " --manifest <asset-manifest.json> [--no-viewer]"
           " [--realtime-sync-cycle-msec <0..>]\n\n"
        << "The manifest resolves the MuJoCo excavator, arm trajectory, "
           "crawler Twist, and joint-state configuration.\n\n"
        << "Options:\n"
        << "  --realtime-sync-cycle-msec <0..>\n"
        << "                Reconcile simulation and wall time at this simulation-time interval.\n"
        << "                0 (default) disables wall-clock pacing.\n\n"
        << "Environment:\n"
        << "  HAKO_ROBOT_EXCAVATOR_MANIFEST       Default manifest when no argument is supplied\n"
        << "  HAKO_ROBOT_EXCAVATOR_ASSET_NAME     Override manifest.name for asset registration\n"
        << "  HAKO_ROBOT_EXCAVATOR_ENDPOINT_NAME  Endpoint instance name, default "
        << kDefaultEndpointName << "\n";
}

void PrintHelp()
{
    std::cout
        << "\nControls:\n"
        << "  p      : pause / resume MuJoCo stepping\n"
        << "  r      : reset the MuJoCo state and clear the active trajectory\n"
        << "  h      : show this help\n"
        << "  q / Esc: stop the asset and close the viewer\n\n"
        << "PDU:\n"
        << "  Receives trajectory_msgs/JointTrajectory on:\n"
        << "    " << trajectory_pdu_robot << "/" << trajectory_pdu_name << "\n\n"
        << "  Publishes sensor_msgs/JointState on:\n"
        << "    " << joint_state_pdu_robot << "/" << joint_state_pdu_name
        << "\n\n"
        << "  Receives geometry_msgs/Twist on:\n"
        << "    " << mobile_base->PduRobot() << "/" << mobile_base->PduName()
        << "\n\n  Receives manual std_msgs/Float64MultiArray on:\n"
        << "    " << excavator_controller->PduRobot() << "/"
        << excavator_controller->ManualJointPduName()
        << "\n\n  Receives manual geometry_msgs/Twist on:\n"
        << "    " << excavator_controller->PduRobot() << "/"
        << excavator_controller->ManualBasePduName()
        << "\n" << std::endl;
}

void PrintState()
{
    if (joint_state_sensor == nullptr || world == nullptr || world->getData() == nullptr) {
        return;
    }

    hako::robots::sensor::JointStateFrame frame {};
    joint_state_sensor->Build(frame);

    std::cout
        << std::fixed << std::setprecision(3)
        << "time=" << std::setw(7) << world->getData()->time
        << " q=[";

    for (std::size_t index = 0; index < frame.position.size(); ++index) {
        if (index > 0) {
            std::cout << ", ";
        }
        std::cout << frame.position[index];
    }

    auto* model = world->getModel();
    auto* data = world->getData();
    const int base_body_id = mj_name2id(model, mjOBJ_BODY, "base_link");
    const int base_joint_id = mj_name2id(model, mjOBJ_JOINT, "base_freejoint");

    std::cout << "]";
    if (base_body_id >= 0 && base_joint_id >= 0) {
        const int qpos_address = model->jnt_qposadr[base_joint_id];
        const int dof_address = model->jnt_dofadr[base_joint_id];
        std::cout
            << " base_xy=[" << data->qpos[qpos_address]
            << ", " << data->qpos[qpos_address + 1] << "]"
            << " base_z=" << data->qpos[qpos_address + 2]
            << " base_vz=" << data->qvel[dof_address + 2]
            << " up_z=" << data->xmat[9 * base_body_id + 8]
            << " ncon=" << data->ncon;
    }

    std::cout << " ctrl=[";

    for (int actuator_index = 0;
        actuator_index < model->nu;
        ++actuator_index)
    {
        if (actuator_index > 0) {
            std::cout << ", ";
        }
        std::cout << data->ctrl[actuator_index];
    }

    std::cout << "]" << std::endl;
}

void ResetSimulation()
{
    if (world == nullptr || world->getModel() == nullptr || world->getData() == nullptr) {
        return;
    }

    const int home_keyframe_id = mj_name2id(
        world->getModel(), mjOBJ_KEY, kHomeKeyframeName);
    if (home_keyframe_id < 0) {
        std::cerr << "[ERROR] MuJoCo model does not define Recipe home keyframe: "
                  << kHomeKeyframeName << std::endl;
        mj_resetData(world->getModel(), world->getData());
    } else {
        mj_resetDataKeyframe(
            world->getModel(), world->getData(), home_keyframe_id);
    }
    mj_forward(world->getModel(), world->getData());
    joint_state_sensor->Reset();
    excavator_controller->Reset();
    std::cout << "[INFO] Excavator simulation reset." << std::endl;
}

static int OnInitialize(hako_asset_context_t* context)
{
    (void)context;
    if (endpoint == nullptr) {
        std::cerr << "[ERROR] Endpoint is not initialized." << std::endl;
        return -1;
    }
    if (endpoint->post_start() != HAKO_PDU_ERR_OK) {
        std::cerr << "[ERROR] Failed to complete endpoint post_start." << std::endl;
        return -1;
    }
    endpoint_ready.store(true);
    return 0;
}

static int OnReset(hako_asset_context_t* context)
{
    (void)context;
    std::lock_guard<std::mutex> lock(mujoco_mutex);
    ResetSimulation();
    return 0;
}

int IsForceStop()
{
    return running.load() && viewer_running.load() ? 0 : 1;
}

static int OnManualTimingControl(hako_asset_context_t* context)
{
    (void)context;

    auto* model = world->getModel();
    const double simulation_timestep_sec = model->opt.timestep;
    const hako_time_t delta_time_usec =
        static_cast<hako_time_t>(simulation_timestep_sec * 1.0e6);
    std::size_t step = 0;
    hakoniwa::robot_runtime::runner::RealtimePacer realtime_pacer(
        realtime_sync_cycle_msec);

    std::cout << "[INFO] Robot excavator Hakoniwa asset started." << std::endl;
    if (viewer_enabled) {
        PrintHelp();
    }

    while (running.load() && viewer_running.load()) {
        bool simulation_advanced = false;
        bool pacing_reset = false;
        double simulation_time_sec = 0.0;
        if (endpoint_ready.load()) {
            std::lock_guard<std::mutex> lock(mujoco_mutex);

            if (reset_requested.exchange(false)) {
                ResetSimulation();
                pacing_reset = true;
            }

            if (!paused.load()) {
                excavator_controller->Update(
                    world->getData()->time, simulation_timestep_sec);
                world->advanceTimeStep();
                simulation_advanced = true;
            } else {
                pacing_reset = true;
            }
            simulation_time_sec = world->getData()->time;

            if (joint_state_sensor->ShouldUpdate(simulation_timestep_sec)) {
                hako::robots::sensor::JointStateFrame frame {};
                joint_state_sensor->Build(frame);
                frame.header.frame_id = "";
                frame.header.stamp_sec = world->getData()->time;
                if (!joint_state_adapter->send(frame)) {
                    std::cerr << "[WARN] Failed to send joint_states PDU." << std::endl;
                }
            }

            if ((step % 500) == 0) {
                PrintState();
            }
            ++step;
        }

        if (print_help_requested.exchange(false)) {
            PrintHelp();
        }

        hako_asset_usleep(delta_time_usec);
        if (pacing_reset) {
            realtime_pacer.reset();
        }
        if (simulation_advanced) {
            realtime_pacer.pace(simulation_time_sec);
        }
    }

    return 0;
}

void HandleViewerKey(int key, int action)
{
#if HAKO_ARM_ENABLE_VIEWER
    if (action != GLFW_PRESS && action != GLFW_REPEAT) {
        return;
    }

    if (key == GLFW_KEY_ESCAPE || key == GLFW_KEY_Q) {
        running.store(false);
        viewer_running.store(false);
    } else if (key == GLFW_KEY_P) {
        paused.store(!paused.load());
        std::cout << "[INFO] " << (paused.load() ? "paused" : "resumed")
                  << std::endl;
    } else if (key == GLFW_KEY_R) {
        reset_requested.store(true);
    } else if (key == GLFW_KEY_H) {
        print_help_requested.store(true);
    }
#else
    (void)key;
    (void)action;
#endif
}

} // namespace

int main(int argc, char** argv)
{
    manifest_path = EnvOrDefault("HAKO_ROBOT_EXCAVATOR_MANIFEST", "");

#if !HAKO_ARM_ENABLE_VIEWER
    viewer_enabled = false;
#endif

    bool positional_manifest_seen = false;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--help") {
            PrintUsage(argv[0]);
            return 0;
        }
        if (argument == "--no-viewer") {
            viewer_enabled = false;
            continue;
        }
        if (argument == "--realtime-sync-cycle-msec") {
            if (++index >= argc || argv[index][0] == '-') {
                PrintUsage(argv[0]);
                return 1;
            }
            try {
                std::size_t parsed = 0;
                const auto value = std::stoull(argv[index], &parsed);
                if (parsed != std::string(argv[index]).size()) {
                    throw std::invalid_argument("trailing characters");
                }
                realtime_sync_cycle_msec = value;
            } catch (const std::exception&) {
                std::cerr << "[ERROR] --realtime-sync-cycle-msec expects an integer >= 0."
                          << std::endl;
                return 1;
            }
            continue;
        }
        if (argument == "--manifest") {
            if (++index >= argc) {
                PrintUsage(argv[0]);
                return 1;
            }
            manifest_path = argv[index];
            positional_manifest_seen = true;
            continue;
        }
        if (!argument.empty() && argument[0] != '-' && !positional_manifest_seen) {
            manifest_path = argument;
            positional_manifest_seen = true;
            continue;
        }
        PrintUsage(argv[0]);
        return 1;
    }

    if (manifest_path.empty()) {
        PrintUsage(argv[0]);
        return 1;
    }

    manifest_path = std::filesystem::absolute(manifest_path).lexically_normal().string();

    hako::robots::config::AssetManifest manifest {};
    std::string manifest_error;
    if (!hako::robots::config::LoadAssetManifestFromJson(
            manifest_path,
            manifest,
            &manifest_error))
    {
        std::cerr << "[ERROR] Failed to load asset manifest: "
                  << manifest_error << std::endl;
        return 1;
    }

    const auto* trajectory_component = manifest.FindComponent("joint_actuator");
    const auto* joint_state_component = manifest.FindComponent("joint_states");
    const auto* mobile_base_component = manifest.FindComponent("mobile_base");
    const auto* controller_component = manifest.FindComponent("excavator_controller");
    if (trajectory_component == nullptr || joint_state_component == nullptr ||
        mobile_base_component == nullptr || controller_component == nullptr)
    {
        std::cerr
            << "[ERROR] Manifest must contain components 'joint_actuator' and "
               "'joint_states', 'mobile_base', and 'excavator_controller': "
            << manifest_path << std::endl;
        return 1;
    }
    if (trajectory_component->pdu_robot.empty() ||
        joint_state_component->pdu_robot.empty())
    {
        std::cerr
            << "[ERROR] Manifest components must define pdu_robot: "
            << manifest_path << std::endl;
        return 1;
    }

    model_path = manifest.model;
    trajectory_config_path = trajectory_component->config;
    joint_state_config_path = joint_state_component->config;
    pdu_def_path = manifest.pdu_def;
    endpoint_config_path = manifest.endpoint;
    trajectory_pdu_robot = trajectory_component->pdu_robot;
    joint_state_pdu_robot = joint_state_component->pdu_robot;
    asset_name = EnvOrDefault(
        "HAKO_ROBOT_EXCAVATOR_ASSET_NAME", manifest.name.c_str());
    endpoint_name = EnvOrDefault(
        "HAKO_ROBOT_EXCAVATOR_ENDPOINT_NAME", kDefaultEndpointName);

    world = std::make_shared<hako::robots::physics::impl::WorldImpl>();
    try {
        world->loadModel(model_path);
    } catch (const std::exception& error) {
        std::cerr << "[ERROR] Failed to load robot arm model: " << error.what()
                  << " path=" << model_path << std::endl;
        return 1;
    }

    auto* model = world->getModel();
    auto* data = world->getData();
    if (model == nullptr || data == nullptr) {
        std::cerr << "[ERROR] MuJoCo model/data is null." << std::endl;
        return 1;
    }

    trajectory_actuator = world->createJointTrajectoryActuator();
    if (!trajectory_actuator->LoadConfig(trajectory_config_path)) {
        std::cerr << "[ERROR] Failed to load trajectory actuator config: "
                  << trajectory_config_path << std::endl;
        return 1;
    }

    joint_state_sensor =
        std::make_unique<hako::robots::sensor::JointStateSensor>(world);
    if (!joint_state_sensor->LoadConfig(joint_state_config_path)) {
        std::cerr << "[ERROR] Failed to load joint state config: "
                  << joint_state_config_path << std::endl;
        return 1;
    }

    mobile_base = std::make_unique<ExcavatorMobileBase>();
    std::string mobile_base_error;
    if (!mobile_base->Load(manifest, world, &mobile_base_error)) {
        std::cerr << "[ERROR] Failed to load excavator mobile base: "
                  << mobile_base_error << std::endl;
        return 1;
    }
    excavator_controller = std::make_unique<ExcavatorController>();
    if (!excavator_controller->Load(
            manifest, world, trajectory_actuator, *joint_state_sensor,
            *mobile_base, &mobile_base_error))
    {
        std::cerr << "[ERROR] Failed to load Excavator Controller: "
                  << mobile_base_error << std::endl;
        return 1;
    }
    ResetSimulation();

    trajectory_pdu_name = trajectory_actuator->GetConfig().pdu_config.pdu_name;
    joint_state_pdu_name = joint_state_sensor->GetConfig().output.pdu_name;

    hako_asset_callbacks_t callbacks {};
    callbacks.on_initialize = OnInitialize;
    callbacks.on_simulation_step = nullptr;
    callbacks.on_manual_timing_control = OnManualTimingControl;
    callbacks.on_reset = OnReset;

    const hako_time_t delta_time_usec =
        static_cast<hako_time_t>(model->opt.timestep * 1.0e6);
    std::cout << "[INFO] Registering robot excavator Hakoniwa asset with:"
              << " name=" << asset_name
              << " delta_time_usec=" << delta_time_usec
              << " manifest=" << manifest_path
              << " model=" << model_path
              << " pdu_def=" << pdu_def_path
              << std::endl;

    hako_conductor_start(delta_time_usec, 100000);

    const int register_result = hako_asset_register(
        asset_name.c_str(),
        pdu_def_path.c_str(),
        &callbacks,
        delta_time_usec,
        HAKO_ASSET_MODEL_PLANT);
    if (register_result != 0) {
        std::cerr << "[ERROR] hako_asset_register() returns "
                  << register_result << std::endl;
        hako_conductor_stop();
        return 1;
    }

    endpoint = std::make_unique<hakoniwa::pdu::Endpoint>(
        endpoint_name,
        HAKO_PDU_ENDPOINT_DIRECTION_INOUT);
    if (endpoint->open(endpoint_config_path) != HAKO_PDU_ERR_OK) {
        std::cerr << "[ERROR] Failed to open endpoint config: "
                  << endpoint_config_path << std::endl;
        hako_conductor_stop();
        return 1;
    }

    const hakoniwa::pdu::PduKey trajectory_key {
        trajectory_pdu_robot,
        trajectory_pdu_name
    };
    const hakoniwa::pdu::PduKey joint_state_key {
        joint_state_pdu_robot,
        joint_state_pdu_name
    };

    if (!excavator_controller->Subscribe(*endpoint, &mobile_base_error)) {
        std::cerr << "[ERROR] Failed to subscribe Excavator Controller: "
                  << mobile_base_error << std::endl;
        endpoint->close();
        endpoint.reset();
        hako_conductor_stop();
        return 1;
    }

    if (!mobile_base->Subscribe(*endpoint, &mobile_base_error)) {
        std::cerr << "[ERROR] Failed to subscribe excavator cmd_vel: "
                  << mobile_base_error << std::endl;
        endpoint->close();
        endpoint.reset();
        hako_conductor_stop();
        return 1;
    }

    if (endpoint->start() != HAKO_PDU_ERR_OK) {
        std::cerr << "[ERROR] Failed to start endpoint." << std::endl;
        endpoint->close();
        endpoint.reset();
        hako_conductor_stop();
        return 1;
    }

    joint_state_adapter = std::make_unique<
        hako::robots::pdu::adapter::sensor_msgs::JointStatePduAdapter>(
        *endpoint,
        joint_state_key);

    std::cout << "[INFO] Starting robot excavator Hakoniwa asset with:" << std::endl;
    std::cout << "  manifest          : " << manifest_path << std::endl;
    std::cout << "  model             : " << model_path << std::endl;
    std::cout << "  trajectory config : " << trajectory_config_path << std::endl;
    std::cout << "  joint state config: " << joint_state_config_path << std::endl;
    std::cout << "  pdu definition    : " << pdu_def_path << std::endl;
    std::cout << "  endpoint config   : " << endpoint_config_path << std::endl;
    std::cout << "  trajectory PDU    : " << trajectory_pdu_robot << "/"
              << trajectory_pdu_name << std::endl;
    std::cout << "  joint state PDU   : " << joint_state_pdu_robot << "/"
              << joint_state_pdu_name << std::endl;
    std::cout << "  cmd_vel PDU       : " << mobile_base->PduRobot() << "/"
              << mobile_base->PduName() << std::endl;
    std::cout << "  manual joint PDU  : " << excavator_controller->PduRobot() << "/"
              << excavator_controller->ManualJointPduName() << std::endl;
    std::cout << "  manual cmd_vel PDU: " << excavator_controller->PduRobot() << "/"
              << excavator_controller->ManualBasePduName() << std::endl;
    std::cout << "  crawler wheels    : " << mobile_base->LeftWheelCount()
              << " left + " << mobile_base->RightWheelCount() << " right"
              << std::endl;

    int start_result = 0;
    std::atomic_bool asset_thread_finished {false};
    std::thread asset_thread([&]() {
        start_result = hako_asset_start_no_wait(IsForceStop);
        asset_thread_finished.store(true);
        running.store(false);
        viewer_running.store(false);
    });

    if (viewer_enabled) {
#if HAKO_ARM_ENABLE_VIEWER
        MujocoRenderRuntime render_runtime(
            model,
            data,
            viewer_running,
            mujoco_mutex,
            MujocoRenderWindowMode::Visible);
        render_runtime.SetKeyCallback(
            [](int key, int action, int mods) {
                (void)mods;
                HandleViewerKey(key, action);
            });
        render_runtime.Run();
#else
        std::cerr << "[ERROR] Viewer support is not compiled in." << std::endl;
        running.store(false);
#endif
    } else {
        while (running.load() && !asset_thread_finished.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    const bool asset_finished_before_viewer_return =
        asset_thread_finished.load();
    running.store(false);
    viewer_running.store(false);
    if (asset_thread.joinable()) {
        asset_thread.join();
    }

    if (endpoint != nullptr) {
        (void)endpoint->stop();
        endpoint->close();
        endpoint.reset();
    }
    excavator_controller.reset();
    joint_state_adapter.reset();
    joint_state_sensor.reset();
    trajectory_actuator.reset();
    mobile_base.reset();
    world.reset();
    hako_conductor_stop();

    if (start_result != 0 && asset_finished_before_viewer_return) {
        std::cerr << "[ERROR] hako_asset_start_no_wait() returns "
                  << start_result << std::endl;
        return 1;
    }
    return 0;
}
