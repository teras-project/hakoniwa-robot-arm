#pragma once

#include "config/asset_manifest.hpp"
#include "excavator_mobile_base.hpp"
#include "hakoniwa/pdu/adapter/geometry_msgs/twist.hpp"
#include "hakoniwa/pdu/adapter/trajectory_msgs/joint_trajectory.hpp"
#include "hakoniwa/pdu/endpoint.hpp"
#include "physics/physics_impl.hpp"
#include "sensors/joint_state/joint_state_sensor.hpp"
#include "std_msgs/pdu_cpptype_Float64MultiArray.hpp"

#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

class ExcavatorController
{
public:
    enum class Mode { Idle, Auto, Manual };

    ExcavatorController();
    ~ExcavatorController();

    bool Load(
        const hako::robots::config::AssetManifest& manifest,
        const std::shared_ptr<hako::robots::physics::impl::WorldImpl>& world,
        const std::shared_ptr<hako::robots::actuator::IJointTrajectoryActuator>& trajectory,
        hako::robots::sensor::JointStateSensor& joint_state_sensor,
        ExcavatorMobileBase& mobile_base,
        std::string* error_message = nullptr);
    bool Subscribe(hakoniwa::pdu::Endpoint& endpoint, std::string* error_message = nullptr);
    void Update(double simulation_time_sec, double delta_time_sec);
    void Reset();

    Mode CurrentMode() const { return mode_; }
    const std::string& ManualJointPduName() const { return manual_joint_pdu_name_; }
    const std::string& ManualBasePduName() const { return manual_base_pdu_name_; }
    const std::string& PduRobot() const { return pdu_robot_; }
    static const char* ModeName(Mode mode);

private:
    class JointVelocityEventReader;
    bool EnterManual(double simulation_time_sec);
    void ApplyManualArm(double delta_time_sec);

    std::shared_ptr<hako::robots::physics::impl::WorldImpl> world_ {};
    std::shared_ptr<hako::robots::actuator::IJointTrajectoryActuator> trajectory_ {};
    hako::robots::sensor::JointStateSensor* joint_state_sensor_ {nullptr};
    ExcavatorMobileBase* mobile_base_ {nullptr};
    std::vector<std::shared_ptr<hako::robots::actuator::IJointActuator>> manual_actuators_ {};
    std::unique_ptr<hako::robots::pdu::adapter::trajectory_msgs::JointTrajectoryEventReader>
        trajectory_reader_ {};
    std::unique_ptr<hako::robots::pdu::adapter::geometry_msgs::TwistEventReader>
        manual_base_reader_ {};
    std::unique_ptr<JointVelocityEventReader> manual_joint_reader_ {};
    std::vector<double> manual_velocity_ {};
    std::vector<double> manual_velocity_limit_ {};
    std::vector<double> manual_target_ {};
    bool has_manual_target_ {false};
    HakoCpp_Twist manual_base_command_ {};
    Mode mode_ {Mode::Idle};
    double manual_timeout_sec_ {0.5};
    double last_manual_command_time_sec_ {0.0};
    std::string pdu_robot_ {};
    std::string trajectory_pdu_name_ {};
    std::string manual_joint_pdu_name_ {};
    std::string manual_base_pdu_name_ {};
};
