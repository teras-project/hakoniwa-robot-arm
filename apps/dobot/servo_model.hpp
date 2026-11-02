#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace hakoniwa::dobot {
using Joints = std::array<double, 6>;
constexpr double pi = 3.14159265358979323846;
// Conservative Nova5 limits, radians, matching the model/official URDF.
constexpr Joints limits {6.28, 3.14, 2.79, 6.28, 6.28, 6.28};

class ServoModel {
public:
    void observe(const Joints& q, const Joints& velocity, double time) {
        actual_ = q;
        velocity_ = velocity;
        now_ = time;
        if (!initialized_) { hold_ = q; initialized_ = true; }
        if (moving_ && now_ >= start_time_ + duration_) {
            bool arrived = true;
            for (int i = 0; i < 6; ++i)
                arrived &= std::abs(q[i] - target_[i]) < .002 && std::abs(velocity[i]) < .01;
            if (arrived) { moving_ = false; hold_ = target_; }
        }
    }
    int enable() { stop(); enabled_ = true; return 0; }
    int disable() { stop(); enabled_ = false; return 0; }
    int stop() { moving_ = false; hold_ = actual_; return 0; }
    void reset() { enabled_ = false; moving_ = false; initialized_ = false; }
    int mode() const { return !enabled_ ? 4 : moving_ ? 7 : 5; }
    const Joints& actual() const { return actual_; }
    int servo(const Joints& degrees, const std::vector<std::string>& params) {
        if (!enabled_) return -3;
        double duration = .1;
        bool has_t = false;
        try {
            for (const auto& param : params) {
                if (param.rfind("t=", 0) != 0 || has_t) return -1;
                std::size_t consumed = 0;
                duration = std::stod(param.substr(2), &consumed);
                if (consumed != param.size() - 2) return -1;
                has_t = true;
            }
        } catch (const std::exception&) { return -1; }
        if (!std::isfinite(duration) || duration < .004 || duration > 120.) return -1;
        Joints radians;
        for (int i = 0; i < 6; ++i) {
            radians[i] = degrees[i] * pi / 180.;
            if (!std::isfinite(radians[i]) || std::abs(radians[i]) > limits[i]) return -1;
        }
        from_ = actual_;
        target_ = radians;
        start_time_ = now_;
        duration_ = duration;
        moving_ = true;
        return 0; // Accepted; arrival is reported by mode()/measured state.
    }
    Joints command() const {
        if (!moving_) return hold_;
        const double u = std::clamp((now_ - start_time_) / duration_, 0., 1.);
        Joints result;
        for (int i = 0; i < 6; ++i) result[i] = from_[i] + u * (target_[i] - from_[i]);
        return result;
    }
private:
    bool initialized_ {false}, enabled_ {false}, moving_ {false};
    double now_ {0}, start_time_ {0}, duration_ {.1};
    Joints actual_ {}, velocity_ {}, hold_ {}, from_ {}, target_ {};
};
}
