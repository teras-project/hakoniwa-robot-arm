#include "servo_model.hpp"
#include <cassert>
#include <limits>

int main() {
    using namespace hakoniwa::dobot;
    ServoModel model;
    Joints zero {};
    model.observe(zero, zero, 0);
    assert(model.mode() == 4);
    assert(model.servo({5,0,0,0,0,0}, {"t=1"}) != 0);
    model.enable();
    assert(model.servo({5,0,0,0,0,0}, {"t=1"}) == 0);
    model.observe(zero, zero, .5);
    assert(std::abs(model.command()[0] - 2.5 * pi / 180.) < 1e-12);
    // Stop captures actual position, never the unfinished target.
    Joints actual {.01, 0,0,0,0,0};
    model.observe(actual, zero, .6); model.stop();
    model.observe(actual, zero, 3.);
    assert(model.command() == actual && model.mode() == 5);
    assert(model.servo({400,0,0,0,0,0}, {"t=1"}) != 0);
    assert(model.servo(zero, {"t=nan"}) != 0);
    assert(model.servo(zero, {"t=1", "gain=10"}) != 0);
    assert(model.command() == actual);
    assert(model.speed_factor(10) == 0);
    assert(model.speed_factor(0) != 0 && model.speed_factor(101) != 0);
    assert(model.move({6,0,0,0,0,0}, true, {}, false) == 0);
    assert(model.move({0,0,0,0,0,0}, true, {}, false) == 0);
    model.observe(actual, zero, 3.1);
    assert(model.command()[0] > actual[0]);
    Joints first_target {6 * pi / 180., 0,0,0,0,0};
    model.observe(first_target, zero, 4.2);
    assert(model.mode() == 7); // Second official-demo MovJ must still be queued.
    model.observe(first_target, zero, 4.5);
    assert(model.command()[0] < first_target[0]);
    model.observe(zero, zero, 6.);
    assert(model.mode() == 5 && model.command() == zero);
    assert(model.move(zero, false, {}, false) != 0);
    assert(model.move(zero, true, {"SpeedJ=100"}, false) != 0);
    assert(model.move({400,0,0,0,0,0}, true, {}, true) != 0);
    assert(model.move({6,0,0,0,0,0}, true, {}, true) == 0);
    model.stop();
    assert(model.set_digital_output(1, 1, 500) == 0);
    assert(model.digital_output(1) == 1);
    model.observe(zero, zero, 6.6);
    assert(model.digital_output(1) == 0);
    assert(model.set_digital_output(1, 1, 0) == 0);
    assert(model.set_digital_output(1, 0, 500) == 0);
    model.observe(zero, zero, 7.2);
    assert(model.digital_output(1) == 1);
    assert(model.set_digital_output(0, 1, 0) != 0);
    assert(model.set_digital_output(1, 2, 0) != 0);
    model.disable(); assert(model.mode() == 4);

    ServoModel queued;
    queued.observe(zero, zero, 0);
    queued.enable();
    assert(queued.move({5,0,0,0,0,0}, true, {}, false) == 0);
    for (int i = 0; i < 16; ++i)
        assert(queued.move(zero, true, {}, false) == 0);
    assert(queued.move(zero, true, {}, false) != 0);
    queued.stop();
    assert(queued.mode() == 5 && queued.command() == zero);
}
