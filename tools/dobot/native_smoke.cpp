// Headless integration harness: production Dobot controller/RPC with real MuJoCo physics.
#include "backend.hpp"
#include <mujoco/mujoco.h>
#include <chrono>
#include <iostream>
#include <thread>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const char* xml = R"(<mujoco><option timestep="0.002" gravity="0 0 0"/>
    <worldbody>
      <body pos="0 0 0"><joint name="joint1" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
      <body pos="1 0 0"><joint name="joint2" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
      <body pos="2 0 0"><joint name="joint3" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
      <body pos="3 0 0"><joint name="joint4" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
      <body pos="4 0 0"><joint name="joint5" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
      <body pos="5 0 0"><joint name="joint6" type="hinge" damping="1"/><geom type="sphere" size="0.05" mass="1"/></body>
    </worldbody><actuator>
      <position joint="joint1" kp="100" kv="1"/><position joint="joint2" kp="100" kv="1"/>
      <position joint="joint3" kp="100" kv="1"/><position joint="joint4" kp="100" kv="1"/>
      <position joint="joint5" kp="100" kv="1"/><position joint="joint6" kp="100" kv="1"/>
    </actuator></mujoco>)";
    mjVFS vfs; mj_defaultVFS(&vfs);
    mj_addBufferVFS(&vfs, "test.xml", xml, static_cast<int>(std::char_traits<char>::length(xml)));
    char error[1024];
    mjModel* m = mj_loadXML("test.xml", &vfs, error, sizeof(error));
    mj_deleteVFS(&vfs);
    if (!m) { std::cerr << error; return 1; }
    mjData* d = mj_makeData(m);
    using namespace hakoniwa::dobot;
    auto model = std::make_shared<ServoModel>();
    auto channel = std::make_shared<DobotRpcChannel>(argv[1], argv[2], "dobot_virtual");
    DobotRpcSource source(channel);
    ServoController controller(model, channel);
    DobotRpcPublisher publisher(model, channel);
    auto deadline = std::chrono::steady_clock::now();
    while (d->time < 45.) {
        rt::RobotState state; state.sample_time_usec = static_cast<std::uint64_t>(d->time * 1'000'000. + .5);
        for (int i = 0; i < 6; ++i) state.actuators.push_back({
            "joint" + std::to_string(i + 1), d->qpos[i], d->qvel[i], 0., state.sample_time_usec});
        rt::RuntimeStepContext context; context.simulation_time_usec = state.sample_time_usec; context.delta_time_usec = 2000;
        const auto polled = source.poll(context);
        const auto output = controller.update(polled.input, state, context);
        for (int i = 0; i < 6; ++i) d->ctrl[i] = output.commands[i].value;
        mj_step(m, d);
        state.sample_time_usec += 2000;
        for (int i = 0; i < 6; ++i) { state.actuators[i].position_rad = d->qpos[i]; state.actuators[i].velocity_rad_per_sec = d->qvel[i]; }
        std::vector<rt::ProcessedInput> inputs;
        if (polled.input)
            inputs.push_back({polled.input->metadata(), rt::InputDelivery::Delivered, {output.status}});
        rt::ArbitrationResult arbitration;
        arbitration.selected_control_id = std::string(controller.id());
        const auto status = publisher.publish(state, context, inputs, arbitration);
        if (status.state == rt::ComponentState::Error) { std::cerr << status.detail; return 1; }
        deadline += std::chrono::milliseconds(2);
        std::this_thread::sleep_until(deadline);
    }
    mj_deleteData(d); mj_deleteModel(m);
}
