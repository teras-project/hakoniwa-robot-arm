#pragma once
#include "servo_model.hpp"
#include "runtime/source/command_source.hpp"
#include "runtime/controller/controller.hpp"
#include "runtime/publisher/state_publisher.hpp"
#include "hakoniwa/pdu/rpc/rpc_service_helper.hpp"
#include <chrono>
#include <deque>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <mutex>
#include <optional>
#include <sstream>
#include <thread>
#include <unordered_map>
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

class DobotRpcChannel final {
public:
    struct Reply {
        rpc::RpcMuxRequest request;
        int result;
    };

    DobotRpcChannel(const std::string& services, const std::string& endpoints,
                    const std::string& node)
        : server_(node, "RpcServerEndpointImpl", services, endpoints, 1000) {
        if (!server_.initialize() || !server_.start())
            throw std::runtime_error("Dobot RPC server startup failed");
        worker_ = std::jthread([this](std::stop_token stop) { receive(stop); });
    }
    ~DobotRpcChannel() {
        worker_.request_stop();
        worker_.join();
        server_.stop();
    }

    std::optional<rpc::RpcMuxRequest> take() {
        std::lock_guard lock(mutex_);
        if (error_) std::rethrow_exception(error_);
        if (requests_.empty()) return std::nullopt;
        auto request = std::move(requests_.front());
        requests_.pop_front();
        return request;
    }

    void stage(std::uint64_t token, rpc::RpcMuxRequest request) {
        if (!pending_.emplace(token, std::move(request)).second)
            throw std::runtime_error("Duplicate Dobot RPC request token");
    }

    void enqueue_reply(std::uint64_t token, int result) {
        auto request = pending_.find(token);
        if (request == pending_.end())
            throw std::runtime_error("Unknown Dobot RPC request token");
        replies_.push_back({std::move(request->second), result});
        pending_.erase(request);
    }

    std::deque<Reply> take_replies() {
        std::deque<Reply> replies;
        replies.swap(replies_);
        return replies;
    }

    rpc::RpcServicesMuxServer& server() noexcept { return server_; }

private:
    void receive(std::stop_token stop) noexcept {
        try {
            while (!stop.stop_requested()) {
                bool full;
                {
                    std::lock_guard lock(mutex_);
                    full = requests_.size() >= 64;
                }
                if (full) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    continue;
                }
                rpc::RpcMuxRequest incoming;
                const auto event = server_.poll(incoming);
                if (event == rpc::ServerEventType::REQUEST_CANCEL) {
                    rpc::PduData reply;
                    if (!server_.create_reply_buffer(incoming, rpc::HAKO_SERVICE_STATUS_DONE,
                            rpc::HAKO_SERVICE_RESULT_CODE_CANCELED, reply)
                        || !server_.send_cancel_reply(incoming, reply))
                        throw std::runtime_error("RPC cancel reply failed");
                } else if (event != rpc::ServerEventType::NONE) {
                    std::lock_guard lock(mutex_);
                    requests_.push_back(std::move(incoming));
                } else {
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                }
            }
        } catch (...) {
            std::lock_guard lock(mutex_);
            error_ = std::current_exception();
        }
    }

    rpc::RpcServicesMuxServer server_;
    std::jthread worker_;
    std::mutex mutex_;
    std::deque<rpc::RpcMuxRequest> requests_;
    std::unordered_map<std::uint64_t, rpc::RpcMuxRequest> pending_;
    std::deque<Reply> replies_;
    std::exception_ptr error_;
};

struct DobotCommand {
    enum class Kind {
        RequestControl, EnableRobot, DisableRobot, ServoJ, Stop,
        GetAngle, RobotMode, ClearError, GetErrorID
    };
    Kind kind;
    std::uint64_t token;
    Joints degrees {};
    std::vector<std::string> parameters;
};

class DobotRpcInput final : public rt::IControllerInput {
public:
    DobotRpcInput(rt::ControllerInputMetadata metadata, DobotCommand command)
        : metadata_(std::move(metadata)), command_(std::move(command)) {}
    const rt::ControllerInputMetadata& metadata() const noexcept override { return metadata_; }
    std::string_view type_name() const noexcept override { return "Dobot/Command"; }
    const DobotCommand& command() const noexcept { return command_; }
private:
    rt::ControllerInputMetadata metadata_;
    DobotCommand command_;
};

class DobotRpcSource final : public rt::ICommandSource {
public:
    explicit DobotRpcSource(std::shared_ptr<DobotRpcChannel> channel)
        : channel_(std::move(channel)) {}
    std::string_view id() const noexcept override { return "dobot-rpc"; }
    rt::CommandSourcePollResult poll(const rt::RuntimeStepContext& context) override {
        auto request = channel_->take();
        if (!request) return {nullptr, {std::string(id()), rt::ComponentState::WaitingForInput, {}}};
        if (sequence_ == std::numeric_limits<std::uint64_t>::max())
            throw std::runtime_error("Dobot RPC sequence exhausted");
        auto command = decode(*request);
        command.token = ++sequence_;
        auto input = std::make_shared<DobotRpcInput>(
            rt::ControllerInputMetadata{std::string(id()), sequence_,
                context.simulation_time_usec, {}}, std::move(command));
        channel_->stage(sequence_, std::move(*request));
        return {std::move(input), {std::string(id()), rt::ComponentState::Ready, {}}};
    }
    // Keep tokens unique across resets until outstanding responses are sent.
    void reset() noexcept override {}
private:
    template<class Wire, class Request>
    Request read(rpc::RpcMuxRequest& incoming) {
        Wire wire;
        Request request {};
        if (!wire.get_request_body(incoming.request, request))
            throw std::runtime_error("Malformed Dobot RPC request");
        return request;
    }
    DobotCommand decode(rpc::RpcMuxRequest& incoming) {
        const auto& name = incoming.request.header.service_name;
        using Kind = DobotCommand::Kind;
        if (name == "Dobot/RequestControl") {
            (void)read<RequestControlWire, HakoCpp_RequestControlRequest>(incoming);
            return {Kind::RequestControl, 0};
        }
        if (name == "Dobot/EnableRobot") {
            (void)read<EnableRobotWire, HakoCpp_EnableRobotRequest>(incoming);
            return {Kind::EnableRobot, 0};
        }
        if (name == "Dobot/DisableRobot") {
            (void)read<DisableRobotWire, HakoCpp_DisableRobotRequest>(incoming);
            return {Kind::DisableRobot, 0};
        }
        if (name == "Dobot/ServoJ") {
            auto request = read<ServoJWire, HakoCpp_ServoJRequest>(incoming);
            return {Kind::ServoJ, 0, {request.a, request.b, request.c,
                request.d, request.e, request.f}, std::move(request.param_value)};
        }
        if (name == "Dobot/Stop") {
            (void)read<StopWire, HakoCpp_StopRequest>(incoming);
            return {Kind::Stop, 0};
        }
        if (name == "Dobot/GetAngle") {
            (void)read<GetAngleWire, HakoCpp_GetAngleRequest>(incoming);
            return {Kind::GetAngle, 0};
        }
        if (name == "Dobot/RobotMode") {
            (void)read<RobotModeWire, HakoCpp_RobotModeRequest>(incoming);
            return {Kind::RobotMode, 0};
        }
        if (name == "Dobot/ClearError") {
            (void)read<ClearErrorWire, HakoCpp_ClearErrorRequest>(incoming);
            return {Kind::ClearError, 0};
        }
        if (name == "Dobot/GetErrorID") {
            (void)read<GetErrorIDWire, HakoCpp_GetErrorIDRequest>(incoming);
            return {Kind::GetErrorID, 0};
        }
        throw std::runtime_error("Unknown Dobot service: " + name);
    }
    std::shared_ptr<DobotRpcChannel> channel_;
    std::uint64_t sequence_ {0};
};

class ServoController final : public rt::IController {
public:
    ServoController(std::shared_ptr<ServoModel> model, std::shared_ptr<DobotRpcChannel> channel)
        : model_(std::move(model)), channel_(std::move(channel)) {}
    std::string_view id() const noexcept override { return "dobot-servo"; }
    std::string_view source_id() const noexcept override { return "dobot-rpc"; }
    bool accepts(const rt::IControllerInput& input) const noexcept override {
        return input.type_name() == "Dobot/Command";
    }
    rt::ControllerOutput update(std::shared_ptr<const rt::IControllerInput> input,
        const rt::RobotState& state, const rt::RuntimeStepContext& context) override {
        observe(*model_, state);
        if (input) {
            const auto& command = static_cast<const DobotRpcInput&>(*input).command();
            channel_->enqueue_reply(command.token, dispatch(command));
        }
        const auto q = model_->command();
        std::vector<rt::ActuatorCommand> commands;
        for (int i = 0; i < 6; ++i) commands.push_back({
            "joint" + std::to_string(i + 1), rt::ActuatorCommandType::Position, q[i],
            std::string(source_id()), context.simulation_time_usec,
            context.simulation_time_usec + context.delta_time_usec});
        return {std::string(id()), {std::string(id()), rt::ComponentState::Ready, {}},
            std::move(commands)};
    }
    void reset(const rt::RobotState& state) override { model_->reset(); observe(*model_, state); }
private:
    int dispatch(const DobotCommand& command) {
        using Kind = DobotCommand::Kind;
        switch (command.kind) {
        case Kind::RequestControl: return 0;
        case Kind::EnableRobot: return model_->enable();
        case Kind::DisableRobot: return model_->disable();
        case Kind::ServoJ: return model_->servo(command.degrees, command.parameters);
        case Kind::Stop: return model_->stop();
        case Kind::GetAngle:
        case Kind::RobotMode:
        case Kind::ClearError:
        case Kind::GetErrorID: return 0;
        }
        throw std::runtime_error("Unknown Dobot command");
    }
    std::shared_ptr<ServoModel> model_;
    std::shared_ptr<DobotRpcChannel> channel_;
};

// Only the Publisher sends responses, after the Plant has produced the observed state.
class DobotRpcPublisher final : public rt::IStatePublisher {
public:
    DobotRpcPublisher(std::shared_ptr<ServoModel> model, std::shared_ptr<DobotRpcChannel> channel)
        : model_(std::move(model)), channel_(std::move(channel)) {}
    std::string_view id() const noexcept override { return "dobot-rpc-replies"; }
    void reset() noexcept override {}
    rt::ComponentStatus publish(const rt::RobotState& state,
                                const rt::RuntimeStepContext&) noexcept override {
        try {
            observe(*model_, state);
            for (auto& reply : channel_->take_replies()) send(reply);
            return {std::string(id()), rt::ComponentState::Ready, {}};
        } catch (const std::exception& error) {
            model_->disable();
            std::cerr << "Dobot RPC response error: " << error.what() << std::endl;
            return {std::string(id()), rt::ComponentState::Error, error.what()};
        }
    }
private:
    template<class Wire, class Response>
    void send_body(DobotRpcChannel::Reply& reply, Response response) {
        Wire wire;
        if (!wire.reply(channel_->server(), reply.request, rpc::HAKO_SERVICE_STATUS_DONE,
                        rpc::HAKO_SERVICE_RESULT_CODE_OK, response))
            throw std::runtime_error("Dobot RPC response failed");
    }
    template<class Wire, class Response>
    void send_result(DobotRpcChannel::Reply& reply) {
        Response response {};
        response.res = reply.result;
        send_body<Wire>(reply, response);
    }
    void send(DobotRpcChannel::Reply& reply) {
        const auto& name = reply.request.request.header.service_name;
        if (name == "Dobot/RequestControl")
            send_result<RequestControlWire, HakoCpp_RequestControlResponse>(reply);
        else if (name == "Dobot/EnableRobot")
            send_result<EnableRobotWire, HakoCpp_EnableRobotResponse>(reply);
        else if (name == "Dobot/DisableRobot")
            send_result<DisableRobotWire, HakoCpp_DisableRobotResponse>(reply);
        else if (name == "Dobot/ServoJ")
            send_result<ServoJWire, HakoCpp_ServoJResponse>(reply);
        else if (name == "Dobot/Stop")
            send_result<StopWire, HakoCpp_StopResponse>(reply);
        else if (name == "Dobot/GetAngle") {
            std::ostringstream out;
            out << '{' << std::fixed << std::setprecision(6);
            const auto q = model_->actual();
            for (int i = 0; i < 6; ++i) {
                if (i) out << ',';
                out << q[i] * 180. / pi;
            }
            out << '}';
            HakoCpp_GetAngleResponse response {};
            response.res = reply.result;
            response.robot_return = out.str();
            send_body<GetAngleWire>(reply, response);
        } else if (name == "Dobot/RobotMode") {
            HakoCpp_RobotModeResponse response {};
            response.res = reply.result;
            response.robot_return = "{" + std::to_string(model_->mode()) + "}";
            send_body<RobotModeWire>(reply, response);
        } else if (name == "Dobot/ClearError")
            send_result<ClearErrorWire, HakoCpp_ClearErrorResponse>(reply);
        else if (name == "Dobot/GetErrorID") {
            HakoCpp_GetErrorIDResponse response {};
            response.res = reply.result;
            response.robot_return = "{[]}";
            send_body<GetErrorIDWire>(reply, response);
        } else throw std::runtime_error("Unknown Dobot service: " + name);
    }
    std::shared_ptr<ServoModel> model_;
    std::shared_ptr<DobotRpcChannel> channel_;
};
}
