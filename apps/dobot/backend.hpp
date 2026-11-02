#pragma once
#include "servo_model.hpp"
#include "runtime/controller/controller.hpp"
#include "runtime/publisher/state_publisher.hpp"
#include "hakoniwa/pdu/rpc/rpc_service_helper.hpp"
#include <iomanip>
#include <sstream>
// Registry's C++ string[] template currently uses cpp-named primitive helpers
// while the common header exports ros-named helpers with the same std::string API.
#include "pdu_primitive_ctypes_conv.hpp"
inline int hako_convert_pdu2cpp_array_string_varray(const Hako_cstring* src,
        std::vector<std::string>& dst, int n) {
    return hako_convert_pdu2ros_array_string_varray(src, dst, n);
}
inline int hako_convert_cpp2pdu_array_string_varray(const std::vector<std::string>& src,
        Hako_cstring* dst) {
    return hako_convert_ros2pdu_array_string_varray(src, dst);
}
// Generated from the installed official .srv files by tools/dobot/generate_types.py.
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RequestControlRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RequestControlResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_EnableRobotRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_EnableRobotResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DisableRobotRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DisableRobotResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_StopRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_StopResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_GetAngleRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_GetAngleResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RobotModeRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RobotModeResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ClearErrorRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ClearErrorResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_GetErrorIDRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_GetErrorIDResponsePacket.hpp"

namespace hakoniwa::dobot {
namespace rt = ::hakoniwa::robot_runtime::runtime;
namespace rpc = ::hakoniwa::pdu::rpc;
using RequestControlWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_RequestControlRequestPacket, HakoCpp_RequestControlResponsePacket,
    HakoCpp_RequestControlRequest, HakoCpp_RequestControlResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::RequestControlRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::RequestControlResponsePacket>;
using EnableRobotWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_EnableRobotRequestPacket, HakoCpp_EnableRobotResponsePacket,
    HakoCpp_EnableRobotRequest, HakoCpp_EnableRobotResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::EnableRobotRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::EnableRobotResponsePacket>;
using DisableRobotWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_DisableRobotRequestPacket, HakoCpp_DisableRobotResponsePacket,
    HakoCpp_DisableRobotRequest, HakoCpp_DisableRobotResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::DisableRobotRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::DisableRobotResponsePacket>;
using ServoJWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_ServoJRequestPacket, HakoCpp_ServoJResponsePacket,
    HakoCpp_ServoJRequest, HakoCpp_ServoJResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::ServoJRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::ServoJResponsePacket>;
using StopWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_StopRequestPacket, HakoCpp_StopResponsePacket,
    HakoCpp_StopRequest, HakoCpp_StopResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::StopRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::StopResponsePacket>;
using GetAngleWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_GetAngleRequestPacket, HakoCpp_GetAngleResponsePacket,
    HakoCpp_GetAngleRequest, HakoCpp_GetAngleResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::GetAngleRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::GetAngleResponsePacket>;
using RobotModeWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_RobotModeRequestPacket, HakoCpp_RobotModeResponsePacket,
    HakoCpp_RobotModeRequest, HakoCpp_RobotModeResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::RobotModeRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::RobotModeResponsePacket>;
using ClearErrorWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_ClearErrorRequestPacket, HakoCpp_ClearErrorResponsePacket,
    HakoCpp_ClearErrorRequest, HakoCpp_ClearErrorResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::ClearErrorRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::ClearErrorResponsePacket>;
using GetErrorIDWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_GetErrorIDRequestPacket, HakoCpp_GetErrorIDResponsePacket,
    HakoCpp_GetErrorIDRequest, HakoCpp_GetErrorIDResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::GetErrorIDRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::GetErrorIDResponsePacket>;

inline void observe(ServoModel& model, const rt::RobotState& state) {
    Joints positions {}, velocities {};
    for (int i = 0; i < 6; ++i) {
        const std::string name = "joint" + std::to_string(i + 1);
        const auto it = std::find_if(state.actuators.begin(), state.actuators.end(),
            [&](const auto& actuator) { return actuator.actuator_id == name; });
        if (it == state.actuators.end()) throw std::runtime_error("Missing Nova5 actuator: " + name);
        positions[i] = it->position_rad;
        velocities[i] = it->velocity_rad_per_sec;
    }
    model.observe(positions, velocities, state.sample_time_usec / 1'000'000.);
}

class ServoController final : public rt::IController {
public:
    explicit ServoController(std::shared_ptr<ServoModel> model) : model_(std::move(model)) {}
    std::string_view id() const noexcept override { return "dobot-servo"; }
    std::string_view source_id() const noexcept override { return {}; }
    bool accepts(const rt::IControllerInput&) const noexcept override { return false; }
    rt::ControllerOutput update(std::shared_ptr<const rt::IControllerInput>,
        const rt::RobotState& state, const rt::RuntimeStepContext& context) override {
        observe(*model_, state);
        const auto q = model_->command();
        std::vector<rt::ActuatorCommand> commands;
        for (int i = 0; i < 6; ++i) commands.push_back({
            "joint" + std::to_string(i + 1), rt::ActuatorCommandType::Position, q[i], {},
            context.simulation_time_usec, context.simulation_time_usec + context.delta_time_usec});
        return {std::string(id()), {std::string(id()), rt::ComponentState::Ready, {}}, std::move(commands)};
    }
    void reset(const rt::RobotState& state) override { model_->reset(); observe(*model_, state); }
private:
    std::shared_ptr<ServoModel> model_;
};

// Called after each physics step by the Runtime. Network workers never touch mjData.
class RpcBoundary final : public rt::IStatePublisher {
public:
    RpcBoundary(std::shared_ptr<ServoModel> model, const std::string& services,
                const std::string& endpoints, const std::string& node)
        : model_(std::move(model)), server_(node, "RpcServerEndpointImpl", services, endpoints, 1000) {
        if (!server_.initialize() || !server_.start()) throw std::runtime_error("Dobot RPC server startup failed");
    }
    ~RpcBoundary() override { server_.stop(); }
    std::string_view id() const noexcept override { return "dobot-rpc"; }
    void reset() noexcept override { model_->reset(); }
    rt::ComponentStatus publish(const rt::RobotState& state, const rt::RuntimeStepContext&) noexcept override {
        try {
            observe(*model_, state);
            // Bound network work so a flood cannot starve physics.
            for (int i = 0; i < 16; ++i) {
                rpc::RpcMuxRequest incoming;
                const auto event = server_.poll(incoming);
                if (event == rpc::ServerEventType::NONE) break;
                if (event == rpc::ServerEventType::REQUEST_CANCEL) {
                    rpc::PduData reply;
                    if (!server_.create_reply_buffer(incoming, rpc::HAKO_SERVICE_STATUS_DONE,
                            rpc::HAKO_SERVICE_RESULT_CODE_CANCELED, reply)
                        || !server_.send_cancel_reply(incoming, reply))
                        throw std::runtime_error("RPC cancel reply failed");
                    continue;
                }
                dispatch(incoming);
            }
            return {std::string(id()), rt::ComponentState::Ready, {}};
        } catch (const std::exception& e) {
            // Fail the physical command path too; never let the previous trajectory continue silently.
            model_->disable();
            std::cerr << "Dobot RPC error: " << e.what() << std::endl;
            return {std::string(id()), rt::ComponentState::Error, e.what()};
        }
    }
private:
    template<class Wire, class Request, class Response, class Fn>
    void handle(rpc::RpcMuxRequest& incoming, Fn fn) {
        Wire wire;
        Request request {};
        Response response {};
        if (!wire.get_request_body(incoming.request, request))
            throw std::runtime_error("Malformed Dobot RPC request");
        fn(request, response);
        if (!wire.reply(server_, incoming, rpc::HAKO_SERVICE_STATUS_DONE,
                        rpc::HAKO_SERVICE_RESULT_CODE_OK, response))
            throw std::runtime_error("Dobot RPC response failed");
    }
    void dispatch(rpc::RpcMuxRequest& incoming) {
        const auto& name = incoming.request.header.service_name;
        if (name == "Dobot/RequestControl") {
            handle<RequestControlWire, HakoCpp_RequestControlRequest, HakoCpp_RequestControlResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = 0; });
        }
        else if (name == "Dobot/EnableRobot") {
            handle<EnableRobotWire, HakoCpp_EnableRobotRequest, HakoCpp_EnableRobotResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = model_->enable(); });
        }
        else if (name == "Dobot/DisableRobot") {
            handle<DisableRobotWire, HakoCpp_DisableRobotRequest, HakoCpp_DisableRobotResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = model_->disable(); });
        }
        else if (name == "Dobot/ServoJ") {
            handle<ServoJWire, HakoCpp_ServoJRequest, HakoCpp_ServoJResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = model_->servo({req.a, req.b, req.c, req.d, req.e, req.f}, req.param_value); });
        }
        else if (name == "Dobot/Stop") {
            handle<StopWire, HakoCpp_StopRequest, HakoCpp_StopResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = model_->stop(); });
        }
        else if (name == "Dobot/GetAngle") {
            handle<GetAngleWire, HakoCpp_GetAngleRequest, HakoCpp_GetAngleResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = 0;
                std::ostringstream out; out << '{' << std::fixed << std::setprecision(6);
                const auto q = model_->actual();
                for (int i = 0; i < 6; ++i) { if (i) out << ','; out << q[i] * 180. / pi; }
                out << '}'; res.robot_return = out.str(); });
        }
        else if (name == "Dobot/RobotMode") {
            handle<RobotModeWire, HakoCpp_RobotModeRequest, HakoCpp_RobotModeResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = 0; res.robot_return = "{" + std::to_string(model_->mode()) + "}"; });
        }
        else if (name == "Dobot/ClearError") {
            handle<ClearErrorWire, HakoCpp_ClearErrorRequest, HakoCpp_ClearErrorResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = 0; });
        }
        else if (name == "Dobot/GetErrorID") {
            handle<GetErrorIDWire, HakoCpp_GetErrorIDRequest, HakoCpp_GetErrorIDResponse>(incoming,
                [&](const auto& req, auto& res) { (void)req; res.res = 0; res.robot_return = "{[]}"; });
        }
        else throw std::runtime_error("Unknown Dobot service: " + name);
    }
    std::shared_ptr<ServoModel> model_;
    rpc::RpcServicesMuxServer server_;
};
}
