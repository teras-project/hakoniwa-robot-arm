#include "excavator_mobile_base.hpp"

#include <algorithm>
#include <fstream>
#include <nlohmann/json.hpp>

namespace
{
double Clamp(double value, double low, double high)
{
    return std::max(low, std::min(value, high));
}

bool Fail(std::string* output, const std::string& message)
{
    if (output != nullptr) {
        *output = message;
    }
    return false;
}
} // namespace

bool ExcavatorMobileBase::Load(
    const hako::robots::config::AssetManifest& manifest,
    const std::shared_ptr<hako::robots::physics::impl::WorldImpl>& world,
    std::string* error_message)
{
    const auto* component = manifest.FindComponent("mobile_base");
    if (component == nullptr) {
        return Fail(error_message, "manifest component 'mobile_base' is missing");
    }
    if (component->pdu_robot.empty()) {
        return Fail(error_message, "mobile_base.pdu_robot must not be empty");
    }

    try {
        std::ifstream stream(component->config);
        if (!stream) {
            return Fail(error_message, "cannot open " + component->config);
        }
        const auto root = nlohmann::json::parse(stream);
        const auto& spec = root.at("spec");
        kinematics_.wheel_radius = spec.at("wheel_radius_m").get<double>();
        kinematics_.wheel_separation = spec.at("wheel_separation_m").get<double>();
        kinematics_.left_wheel_sign = spec.at("left_wheel_sign").get<double>();
        kinematics_.right_wheel_sign = spec.at("right_wheel_sign").get<double>();
        kinematics_.max_wheel_angular_velocity =
            spec.at("max_wheel_angular_velocity_rad_s").get<double>();
        max_linear_velocity_m_s_ =
            spec.at("max_linear_velocity_m_s").get<double>();
        max_angular_velocity_rad_s_ =
            spec.at("max_angular_velocity_rad_s").get<double>();
        command_timeout_sec_ = spec.at("command_timeout_sec").get<double>();
        const auto left_components =
            spec.at("left_actuator_components").get<std::vector<std::string>>();
        const auto right_components =
            spec.at("right_actuator_components").get<std::vector<std::string>>();
        pdu_robot_ = component->pdu_robot;
        pdu_name_ = root.at("pdu_config").at("pdu_name").get<std::string>();

        if (kinematics_.wheel_radius <= 0.0 ||
            kinematics_.wheel_separation <= 0.0 ||
            kinematics_.max_wheel_angular_velocity <= 0.0 ||
            max_linear_velocity_m_s_ <= 0.0 ||
            max_angular_velocity_rad_s_ <= 0.0 ||
            command_timeout_sec_ <= 0.0 ||
            left_components.empty() || right_components.empty() ||
            pdu_name_.empty())
        {
            return Fail(error_message, "mobile-base limits, lists, and PDU name must be valid");
        }

        world_ = world;
        if (!LoadActuators(manifest, left_components, left_actuators_, error_message) ||
            !LoadActuators(manifest, right_components, right_actuators_, error_message))
        {
            return false;
        }
        return true;
    } catch (const std::exception& exception) {
        return Fail(error_message, exception.what());
    }
}

bool ExcavatorMobileBase::LoadActuators(
    const hako::robots::config::AssetManifest& manifest,
    const std::vector<std::string>& component_ids,
    std::vector<std::shared_ptr<hako::robots::actuator::IJointActuator>>& output,
    std::string* error_message)
{
    for (const auto& id : component_ids) {
        const auto* component = manifest.FindComponent(id);
        if (component == nullptr || component->config.empty()) {
            return Fail(error_message, "wheel actuator component is missing: " + id);
        }
        auto actuator = world_->createJointActuator();
        if (!actuator->LoadConfig(component->config)) {
            return Fail(error_message, "cannot load wheel actuator: " + component->config);
        }
        output.push_back(std::move(actuator));
    }
    return true;
}

bool ExcavatorMobileBase::Subscribe(
    hakoniwa::pdu::Endpoint& endpoint,
    std::string* error_message)
{
    try {
        command_reader_ = std::make_unique<
            hako::robots::pdu::adapter::geometry_msgs::TwistEventReader>(
            endpoint,
            hakoniwa::pdu::PduKey {pdu_robot_, pdu_name_});
        command_reader_->subscribe();
        return true;
    } catch (const std::exception& exception) {
        command_reader_.reset();
        return Fail(error_message, exception.what());
    }
}

void ExcavatorMobileBase::SetWheelTargets(double left, double right)
{
    for (const auto& actuator : left_actuators_) {
        actuator->SetTarget(left);
    }
    for (const auto& actuator : right_actuators_) {
        actuator->SetTarget(right);
    }
}

void ExcavatorMobileBase::ApplyTwist(const HakoCpp_Twist& command)
{
    const double linear_x = Clamp(
        command.linear.x,
        -max_linear_velocity_m_s_,
        max_linear_velocity_m_s_);
    const double angular_z = Clamp(
        command.angular.z,
        -max_angular_velocity_rad_s_,
        max_angular_velocity_rad_s_);
    const auto targets = hako::robots::rover::ToWheelVelocityTargets(
        linear_x, angular_z, kinematics_);
    SetWheelTargets(targets.left, targets.right);
}

void ExcavatorMobileBase::Update(
    double simulation_time_sec,
    bool auto_command_enabled)
{
    HakoCpp_Twist incoming {};
    if (command_reader_ != nullptr && command_reader_->take(incoming)) {
        latest_command_ = incoming;
        has_command_ = true;
        last_command_time_sec_ = simulation_time_sec;
    }
    if (has_command_ &&
        simulation_time_sec - last_command_time_sec_ > command_timeout_sec_)
    {
        latest_command_ = HakoCpp_Twist {};
        has_command_ = false;
    }

    ApplyTwist(auto_command_enabled ? latest_command_ : HakoCpp_Twist {});
}

void ExcavatorMobileBase::Reset()
{
    latest_command_ = HakoCpp_Twist {};
    has_command_ = false;
    last_command_time_sec_ = 0.0;
    SetWheelTargets(0.0, 0.0);
}
