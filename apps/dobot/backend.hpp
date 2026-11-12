#pragma once
#include "servo_model.hpp"
#include "runtime/source/command_source.hpp"
#include "runtime/source/non_lockstep_request_queue.hpp"
#include "runtime/controller/controller.hpp"
#include "runtime/publisher/request_publisher.hpp"
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
#include "pdu_primitive_ctypes_conv.hpp"
// Generated from the installed official .srv files by tools/dobot/generate_types.py.
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RequestControlRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_RequestControlResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_EnableRobotRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_EnableRobotResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DisableRobotRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DisableRobotResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_MovJRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_MovJResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_MovLRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_MovLResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_SpeedFactorRequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_SpeedFactorResponsePacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DORequestPacket.hpp"
#include "dobot_msgs_v4_msgs/pdu_cpptype_conv_DOResponsePacket.hpp"
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
using MovJWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_MovJRequestPacket, HakoCpp_MovJResponsePacket,
    HakoCpp_MovJRequest, HakoCpp_MovJResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::MovJRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::MovJResponsePacket>;
using MovLWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_MovLRequestPacket, HakoCpp_MovLResponsePacket,
    HakoCpp_MovLRequest, HakoCpp_MovLResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::MovLRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::MovLResponsePacket>;
using SpeedFactorWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_SpeedFactorRequestPacket, HakoCpp_SpeedFactorResponsePacket,
    HakoCpp_SpeedFactorRequest, HakoCpp_SpeedFactorResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::SpeedFactorRequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::SpeedFactorResponsePacket>;
using DOWire = rpc::HakoRpcAssetServiceServer<
    HakoCpp_DORequestPacket, HakoCpp_DOResponsePacket,
    HakoCpp_DORequest, HakoCpp_DOResponse,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::DORequestPacket,
    ::hako::pdu::msgs::dobot_msgs_v4_msgs::DOResponsePacket>;
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
        std::uint64_t token;
        rpc::RpcMuxRequest request;
        int result;
        int transport_result_code;
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
        return requests_.try_take();
    }

    void stage(std::uint64_t token, rpc::RpcMuxRequest request) {
        if (!pending_.emplace(token, std::move(request)).second)
            throw std::runtime_error("Duplicate Dobot RPC request token");
    }

    void enqueue_reply(std::uint64_t token, int result) {
        auto request = pending_.find(token);
        if (request == pending_.end())
            throw std::runtime_error("Unknown Dobot RPC request token");
        replies_.push_back({token, std::move(request->second), result,
            rpc::HAKO_SERVICE_RESULT_CODE_OK});
        pending_.erase(request);
    }

    void enqueue_rejection(std::uint64_t token, int result_code) {
        auto request = pending_.find(token);
        if (request == pending_.end())
            throw std::runtime_error("Unknown Dobot RPC request token");
        replies_.push_back({token, std::move(request->second), 0, result_code});
        pending_.erase(request);
    }

    void enqueue_invalid(rpc::RpcMuxRequest request) {
        replies_.push_back({0, std::move(request), 0,
            rpc::HAKO_SERVICE_RESULT_CODE_INVALID});
    }

    std::deque<Reply> take_replies() {
        std::deque<Reply> replies;
        replies.swap(replies_);
        return replies;
    }

    rpc::RpcServicesMuxServer& server() noexcept { return server_; }

    void cancel_outstanding() noexcept {
        try {
            std::vector<rpc::RpcMuxRequest> requests;
            {
                std::lock_guard lock(mutex_);
                ++generation_;
                requests = requests_.drain();
            }
            for (auto& [token, request] : pending_) {
                (void)token;
                requests.push_back(std::move(request));
            }
            pending_.clear();
            for (auto& reply : replies_) requests.push_back(std::move(reply.request));
            replies_.clear();
            for (const auto& request : requests) {
                rpc::PduData response;
                if (!server_.create_reply_buffer(request, rpc::HAKO_SERVICE_STATUS_ERROR,
                        rpc::HAKO_SERVICE_RESULT_CODE_CANCELED, response)
                    || !server_.send_reply(request, response))
                    throw std::runtime_error("Dobot RPC reset cancellation failed");
            }
        } catch (const std::exception& error) {
            std::cerr << "Dobot RPC reset failed: " << error.what() << std::endl;
            std::lock_guard lock(mutex_);
            error_ = std::current_exception();
        }
    }

private:
    static bool same_request(const rpc::RpcMuxRequest& a,
                             const rpc::RpcMuxRequest& b) {
        return a.connection_id == b.connection_id
            && a.request.header.request_id == b.request.header.request_id
            && a.request.header.client_name == b.request.header.client_name
            && a.request.header.service_name == b.request.header.service_name;
    }

    void receive(std::stop_token stop) noexcept {
        try {
            while (!stop.stop_requested()) {
                std::uint64_t generation;
                {
                    std::lock_guard lock(mutex_);
                    generation = generation_;
                }
                rpc::RpcMuxRequest incoming;
                const auto event = server_.poll(incoming);
                if (event == rpc::ServerEventType::REQUEST_CANCEL) {
                    (void)requests_.remove_if([&](const auto& request) {
                        return same_request(request, incoming);
                    });
                    rpc::PduData reply;
                    if (!server_.create_reply_buffer(incoming, rpc::HAKO_SERVICE_STATUS_DONE,
                            rpc::HAKO_SERVICE_RESULT_CODE_CANCELED, reply)
                        || !server_.send_cancel_reply(incoming, reply))
                        throw std::runtime_error("RPC cancel reply failed");
                } else if (event == rpc::ServerEventType::REQUEST_IN) {
                    bool queued = false;
                    bool stale = false;
                    {
                        std::lock_guard lock(mutex_);
                        stale = generation != generation_;
                        if (!stale) queued = requests_.try_push(incoming);
                    }
                    if (!queued) {
                        rpc::PduData reply;
                        if (!server_.create_reply_buffer(incoming, rpc::HAKO_SERVICE_STATUS_ERROR,
                                stale ? rpc::HAKO_SERVICE_RESULT_CODE_CANCELED
                                      : rpc::HAKO_SERVICE_RESULT_CODE_BUSY, reply)
                            || !server_.send_reply(incoming, reply))
                            throw std::runtime_error("RPC unavailable reply failed");
                    }
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
    std::uint64_t generation_ {0};
    rt::NonLockstepRequestQueue<rpc::RpcMuxRequest> requests_ {64};
    std::unordered_map<std::uint64_t, rpc::RpcMuxRequest> pending_;
    std::deque<Reply> replies_;
    std::exception_ptr error_;
};

struct DobotCommand {
    enum class Kind {
        RequestControl, EnableRobot, DisableRobot, ServoJ, MovJ, MovL,
        SpeedFactor, DO, Stop,
        GetAngle, RobotMode, ClearError, GetErrorID
    };
    Kind kind;
    std::uint64_t token;
    Joints degrees {};
    std::vector<std::string> parameters;
    bool joint_mode {false};
    int ratio {0};
    int index {0};
    int status {0};
    int time_ms {0};
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
        DobotCommand command;
        try {
            command = decode(*request);
        } catch (const std::exception& error) {
            channel_->enqueue_invalid(std::move(*request));
            return {nullptr, {std::string(id()), rt::ComponentState::Degraded, error.what()}};
        }
        command.token = ++sequence_;
        auto input = std::make_shared<DobotRpcInput>(
            rt::ControllerInputMetadata{std::string(id()), sequence_,
                context.simulation_time_usec, {}}, std::move(command));
        channel_->stage(sequence_, std::move(*request));
        return {std::move(input), {std::string(id()), rt::ComponentState::Ready, {}}};
    }
    // Keep tokens unique across resets; stale queued calls must not execute afterward.
    void reset() noexcept override { channel_->cancel_outstanding(); }
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
        if (name == "Dobot/MovJ") {
            auto request = read<MovJWire, HakoCpp_MovJRequest>(incoming);
            DobotCommand command {Kind::MovJ, 0, {request.a, request.b, request.c,
                request.d, request.e, request.f}, std::move(request.param_value)};
            command.joint_mode = request.mode;
            return command;
        }
        if (name == "Dobot/MovL") {
            auto request = read<MovLWire, HakoCpp_MovLRequest>(incoming);
            DobotCommand command {Kind::MovL, 0, {request.a, request.b, request.c,
                request.d, request.e, request.f}, std::move(request.param_value)};
            command.joint_mode = request.mode;
            return command;
        }
        if (name == "Dobot/SpeedFactor") {
            auto request = read<SpeedFactorWire, HakoCpp_SpeedFactorRequest>(incoming);
            DobotCommand command {Kind::SpeedFactor, 0};
            command.ratio = request.ratio;
            return command;
        }
        if (name == "Dobot/DO") {
            auto request = read<DOWire, HakoCpp_DORequest>(incoming);
            DobotCommand command {Kind::DO, 0};
            command.index = request.index;
            command.status = request.status;
            command.time_ms = request.time;
            return command;
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
        case Kind::MovJ: return model_->move(command.degrees, command.joint_mode,
            command.parameters, false);
        case Kind::MovL: return model_->move(command.degrees, command.joint_mode,
            command.parameters, true);
        case Kind::SpeedFactor: return model_->speed_factor(command.ratio);
        case Kind::DO: return model_->set_digital_output(command.index,
            command.status, command.time_ms);
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
class DobotRpcPublisher final : public rt::IRequestPublisher {
public:
    DobotRpcPublisher(std::shared_ptr<ServoModel> model, std::shared_ptr<DobotRpcChannel> channel)
        : model_(std::move(model)), channel_(std::move(channel)) {}
    std::string_view id() const noexcept override { return "dobot-rpc-replies"; }
    void reset() noexcept override {}
    rt::ComponentStatus publish(const rt::RobotState& state,
                                const rt::RuntimeStepContext&,
                                const std::vector<rt::ProcessedInput>& inputs,
                                const rt::ArbitrationResult& arbitration) noexcept override {
        try {
            observe(*model_, state);
            for (const auto& input : inputs) {
                if (input.metadata.source_id == "dobot-rpc"
                    && input.delivery != rt::InputDelivery::Delivered) {
                    channel_->enqueue_rejection(input.metadata.sequence,
                        rpc::HAKO_SERVICE_RESULT_CODE_INVALID);
                }
            }
            for (auto& reply : channel_->take_replies()) {
                if (reply.transport_result_code != rpc::HAKO_SERVICE_RESULT_CODE_OK) {
                    send_error(reply, reply.transport_result_code);
                    continue;
                }
                const auto input = std::find_if(inputs.begin(), inputs.end(),
                    [&](const rt::ProcessedInput& value) {
                        return value.metadata.source_id == "dobot-rpc"
                            && value.metadata.sequence == reply.token;
                    });
                if (input == inputs.end()
                    || input->delivery != rt::InputDelivery::Delivered
                    || input->controller_statuses.size() != 1
                    || !input->controller_statuses[0].can_produce_commands()
                    || arbitration.selected_control_id != "dobot-servo") {
                    send_error(reply, rpc::HAKO_SERVICE_RESULT_CODE_ERROR);
                    continue;
                }
                send(reply);
            }
            return {std::string(id()), rt::ComponentState::Ready, {}};
        } catch (const std::exception& error) {
            model_->disable();
            std::cerr << "Dobot RPC response error: " << error.what() << std::endl;
            return {std::string(id()), rt::ComponentState::Error, error.what()};
        }
    }
private:
    void send_error(const DobotRpcChannel::Reply& reply, int result_code) {
        rpc::PduData error;
        if (!channel_->server().create_reply_buffer(reply.request,
                rpc::HAKO_SERVICE_STATUS_ERROR, result_code, error)
            || !channel_->server().send_reply(reply.request, error))
            throw std::runtime_error("Dobot RPC error response failed");
    }

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
        else if (name == "Dobot/MovJ")
            send_result<MovJWire, HakoCpp_MovJResponse>(reply);
        else if (name == "Dobot/MovL")
            send_result<MovLWire, HakoCpp_MovLResponse>(reply);
        else if (name == "Dobot/SpeedFactor")
            send_result<SpeedFactorWire, HakoCpp_SpeedFactorResponse>(reply);
        else if (name == "Dobot/DO")
            send_result<DOWire, HakoCpp_DOResponse>(reply);
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
