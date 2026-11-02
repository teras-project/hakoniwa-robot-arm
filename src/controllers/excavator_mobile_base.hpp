#pragma once

#include "config/asset_manifest.hpp"
#include "hakoniwa/pdu/adapter/geometry_msgs/twist.hpp"
#include "hakoniwa/pdu/endpoint.hpp"
#include "physics/physics_impl.hpp"
#include "robots/rover/differential_drive_kinematics.hpp"

#include <memory>
#include <string>
#include <vector>

class ExcavatorMobileBase
{
public:
    bool Load(
        const hako::robots::config::AssetManifest& manifest,
        const std::shared_ptr<hako::robots::physics::impl::WorldImpl>& world,
        std::string* error_message = nullptr);
    bool Subscribe(
        hakoniwa::pdu::Endpoint& endpoint,
        std::string* error_message = nullptr);
    void Update(double simulation_time_sec, bool auto_command_enabled = true);
    void ApplyTwist(const HakoCpp_Twist& command);
    void Reset();

    const std::string& PduRobot() const { return pdu_robot_; }
    const std::string& PduName() const { return pdu_name_; }
    std::size_t LeftWheelCount() const { return left_actuators_.size(); }
    std::size_t RightWheelCount() const { return right_actuators_.size(); }

private:
    bool LoadActuators(
        const hako::robots::config::AssetManifest& manifest,
        const std::vector<std::string>& component_ids,
        std::vector<std::shared_ptr<hako::robots::actuator::IJointActuator>>& output,
        std::string* error_message);
    void SetWheelTargets(double left, double right);

    std::shared_ptr<hako::robots::physics::impl::WorldImpl> world_ {};
    hako::robots::rover::DifferentialDriveKinematics kinematics_ {};
    double max_linear_velocity_m_s_ {0.0};
    double max_angular_velocity_rad_s_ {0.0};
    double command_timeout_sec_ {0.5};
    std::vector<std::shared_ptr<hako::robots::actuator::IJointActuator>>
        left_actuators_ {};
    std::vector<std::shared_ptr<hako::robots::actuator::IJointActuator>>
        right_actuators_ {};
    std::unique_ptr<hako::robots::pdu::adapter::geometry_msgs::TwistEventReader>
        command_reader_ {};
    HakoCpp_Twist latest_command_ {};
    bool has_command_ {false};
    double last_command_time_sec_ {0.0};
    std::string pdu_robot_ {};
    std::string pdu_name_ {};
};
