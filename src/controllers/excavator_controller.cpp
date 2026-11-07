#include "excavator_controller.hpp"

#include "std_msgs/pdu_cpptype_conv_Float64MultiArray.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#include <span>
#include <stdexcept>

namespace
{
bool Fail(std::string* output, const std::string& message)
{
    if (output != nullptr) {
        *output = message;
    }
    return false;
}
} // namespace

class ExcavatorController::JointVelocityEventReader
{
public:
    JointVelocityEventReader(
        hakoniwa::pdu::Endpoint& endpoint,
        const hakoniwa::pdu::PduKey& key)
        : endpoint_(endpoint), key_(key)
    {
    }

    void Subscribe()
    {
        const hakoniwa::pdu::PduResolvedKey resolved {
            key_.robot, endpoint_.get_pdu_channel_id(key_)
        };
        if (resolved.channel_id < 0 ||
            endpoint_.set_recv_event(resolved) != HAKO_PDU_ERR_OK)
        {
            throw std::runtime_error("failed to subscribe manual joint velocity PDU");
        }
        endpoint_.subscribe_on_recv_callback(
            resolved,
            [this](const hakoniwa::pdu::PduResolvedKey&,
                   std::span<const std::byte> payload) {
                HakoCpp_Float64MultiArray value {};
                hako::pdu::msgs::std_msgs::Float64MultiArray converter;
                std::vector<std::byte> copy(payload.begin(), payload.end());
                if (!converter.pdu2cpp(reinterpret_cast<char*>(copy.data()), value)) {
                    return;
                }
                std::lock_guard<std::mutex> lock(mutex_);
                pending_ = std::move(value.data);
            });
    }

    bool Take(std::vector<double>& output)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!pending_.has_value()) {
            return false;
        }
        output = std::move(*pending_);
        pending_.reset();
        return true;
    }

private:
    hakoniwa::pdu::Endpoint& endpoint_;
    hakoniwa::pdu::PduKey key_;
    std::mutex mutex_ {};
    std::optional<std::vector<double>> pending_ {};
};

ExcavatorController::ExcavatorController() = default;
ExcavatorController::~ExcavatorController() = default;

const char* ExcavatorController::ModeName(Mode mode)
{
    switch (mode) {
    case Mode::Auto: return "AUTO";
    case Mode::Manual: return "MANUAL";
    default: return "IDLE";
    }
}

bool ExcavatorController::Load(
    const hako::robots::config::AssetManifest& manifest,
    const std::shared_ptr<hako::robots::physics::impl::WorldImpl>& world,
    const std::shared_ptr<hako::robots::actuator::IJointTrajectoryActuator>& trajectory,
    hako::robots::sensor::JointStateSensor& joint_state_sensor,
    ExcavatorMobileBase& mobile_base,
    std::string* error_message)
{
    const auto* component = manifest.FindComponent("excavator_controller");
    if (component == nullptr || component->pdu_robot.empty()) {
        return Fail(error_message, "manifest component 'excavator_controller' is missing");
    }
    try {
        std::ifstream stream(component->config);
        if (!stream) {
            return Fail(error_message, "cannot open " + component->config);
        }
        const auto root = nlohmann::json::parse(stream);
        const auto& spec = root.at("spec");
        manual_timeout_sec_ = spec.at("manual_timeout_sec").get<double>();
        manual_joint_pdu_name_ = spec.at("manual_joint_velocity_pdu").get<std::string>();
        manual_base_pdu_name_ = spec.at("manual_cmd_vel_pdu").get<std::string>();
        const auto actuator_components =
            spec.at("manual_joint_actuator_components").get<std::vector<std::string>>();
        manual_velocity_limit_ =
            spec.at("manual_joint_velocity_limits_rad_s").get<std::vector<double>>();
        if (manual_timeout_sec_ <= 0.0 || actuator_components.empty() ||
            manual_velocity_limit_.size() != actuator_components.size() ||
            std::any_of(
                manual_velocity_limit_.begin(), manual_velocity_limit_.end(),
                [](double value) { return value <= 0.0; }))
        {
            return Fail(error_message, "manual timeout and actuator list must be valid");
        }

        world_ = world;
        trajectory_ = trajectory;
        joint_state_sensor_ = &joint_state_sensor;
        mobile_base_ = &mobile_base;
        pdu_robot_ = component->pdu_robot;
        trajectory_pdu_name_ = trajectory_->GetConfig().pdu_config.pdu_name;
        for (const auto& id : actuator_components) {
            const auto* actuator_component = manifest.FindComponent(id);
            if (actuator_component == nullptr || actuator_component->config.empty()) {
                return Fail(error_message, "manual actuator component is missing: " + id);
            }
            auto actuator = world_->createJointActuator();
            if (!actuator->LoadConfig(actuator_component->config)) {
                return Fail(error_message, "cannot load manual actuator: " + actuator_component->config);
            }
            manual_actuators_.push_back(std::move(actuator));
        }
        manual_velocity_.assign(manual_actuators_.size(), 0.0);
        manual_target_.assign(manual_actuators_.size(), 0.0);
        return true;
    } catch (const std::exception& exception) {
        return Fail(error_message, exception.what());
    }
}

bool ExcavatorController::Subscribe(
    hakoniwa::pdu::Endpoint& endpoint,
    std::string* error_message)
{
    try {
        trajectory_reader_ = std::make_unique<
            hako::robots::pdu::adapter::trajectory_msgs::JointTrajectoryEventReader>(
                endpoint, hakoniwa::pdu::PduKey {pdu_robot_, trajectory_pdu_name_});
        trajectory_reader_->subscribe();
        manual_joint_reader_ = std::make_unique<JointVelocityEventReader>(
            endpoint, hakoniwa::pdu::PduKey {pdu_robot_, manual_joint_pdu_name_});
        manual_joint_reader_->Subscribe();
        manual_base_reader_ = std::make_unique<
            hako::robots::pdu::adapter::geometry_msgs::TwistEventReader>(
                endpoint, hakoniwa::pdu::PduKey {pdu_robot_, manual_base_pdu_name_});
        manual_base_reader_->subscribe();
        return true;
    } catch (const std::exception& exception) {
        return Fail(error_message, exception.what());
    }
}

bool ExcavatorController::EnterManual(double simulation_time_sec)
{
    if (mode_ != Mode::Manual) {
        trajectory_->ClearTrajectory();
        hako::robots::sensor::JointStateFrame frame {};
        joint_state_sensor_->Build(frame);
        if (frame.position.size() != manual_target_.size()) {
            return false;
        }
        manual_target_ = frame.position;
        has_manual_target_ = true;
        manual_velocity_.assign(manual_velocity_.size(), 0.0);
        manual_base_command_ = HakoCpp_Twist {};
        mode_ = Mode::Manual;
        std::cout << "[INFO] Excavator Controller mode: MANUAL" << std::endl;
    }
    last_manual_command_time_sec_ = simulation_time_sec;
    return true;
}

void ExcavatorController::ApplyManualArm(double delta_time_sec)
{
    for (std::size_t index = 0; index < manual_actuators_.size(); ++index) {
        manual_target_[index] += manual_velocity_[index] * delta_time_sec;
        manual_actuators_[index]->SetTarget(manual_target_[index]);
        // Read back the clamped command so integration cannot wind up beyond limits.
        const auto& limit = manual_actuators_[index]->GetConfig().limit;
        if (limit.has_limits) {
            manual_target_[index] = std::max(
                limit.lower, std::min(manual_target_[index], limit.upper));
        }
    }
}

void ExcavatorController::Update(double simulation_time_sec, double delta_time_sec)
{
    std::vector<double> joint_velocity;
    if (manual_joint_reader_ != nullptr && manual_joint_reader_->Take(joint_velocity)) {
        if (joint_velocity.size() != manual_velocity_.size()) {
            std::cerr << "[WARN] Manual joint velocity requires "
                      << manual_velocity_.size() << " values." << std::endl;
        } else if (EnterManual(simulation_time_sec)) {
            for (std::size_t index = 0; index < joint_velocity.size(); ++index) {
                manual_velocity_[index] = std::max(
                    -manual_velocity_limit_[index],
                    std::min(joint_velocity[index], manual_velocity_limit_[index]));
            }
        }
    }
    HakoCpp_Twist manual_twist {};
    if (manual_base_reader_ != nullptr && manual_base_reader_->take(manual_twist) &&
        EnterManual(simulation_time_sec))
    {
        manual_base_command_ = manual_twist;
    }

    hako::robots::actuator::JointTrajectoryTarget trajectory_target {};
    if (trajectory_reader_ != nullptr && trajectory_reader_->take(trajectory_target)) {
        if (mode_ == Mode::Manual) {
            std::cout << "[WARN] Ignored JointTrajectory while MANUAL is active."
                      << std::endl;
        } else if (trajectory_->SetTrajectory(trajectory_target)) {
            mode_ = Mode::Auto;
            std::cout << "[INFO] Accepted JointTrajectory; Excavator Controller mode: AUTO; joints="
                      << trajectory_target.joint_names.size()
                      << " points=" << trajectory_target.points.size() << std::endl;
        } else {
            std::cerr << "[WARN] Rejected invalid JointTrajectory." << std::endl;
        }
    }

    if (mode_ == Mode::Manual &&
        simulation_time_sec - last_manual_command_time_sec_ > manual_timeout_sec_)
    {
        manual_velocity_.assign(manual_velocity_.size(), 0.0);
        manual_base_command_ = HakoCpp_Twist {};
        mode_ = Mode::Idle;
        std::cout << "[INFO] Excavator Controller manual timeout: holding arm and stopping base."
                  << std::endl;
    }

    if (mode_ == Mode::Manual) {
        ApplyManualArm(delta_time_sec);
        mobile_base_->Update(simulation_time_sec, false);
        mobile_base_->ApplyTwist(manual_base_command_);
    } else {
        if (mode_ == Mode::Auto) {
            trajectory_->Update();
        } else {
            // Preserve the final manual position after the deadman timeout.
            if (has_manual_target_) {
                ApplyManualArm(0.0);
            }
        }
        mobile_base_->Update(simulation_time_sec, true);
    }
}

void ExcavatorController::Reset()
{
    trajectory_->ClearTrajectory();
    mobile_base_->Reset();
    manual_velocity_.assign(manual_velocity_.size(), 0.0);
    hako::robots::sensor::JointStateFrame frame {};
    joint_state_sensor_->Build(frame);
    has_manual_target_ = frame.position.size() == manual_target_.size();
    if (has_manual_target_) {
        manual_target_ = frame.position;
    }
    manual_base_command_ = HakoCpp_Twist {};
    last_manual_command_time_sec_ = 0.0;
    mode_ = Mode::Idle;
}
