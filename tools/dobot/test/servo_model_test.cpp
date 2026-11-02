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
    model.disable(); assert(model.mode() == 4);
}
