#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
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
        for (std::size_t i = 0; i < pulse_deadline_.size(); ++i) {
            if (pulse_deadline_[i] >= 0 && now_ >= pulse_deadline_[i]) {
                outputs_[i] = pulse_restore_[i];
                pulse_deadline_[i] = -1;
            }
        }
        if (moving_ && now_ >= start_time_ + duration_) {
            bool arrived = true;
            for (int i = 0; i < 6; ++i)
                arrived &= std::abs(q[i] - target_[i]) < .002 && std::abs(velocity[i]) < .01;
            if (arrived) {
                hold_ = target_;
                moving_ = false;
                if (!queued_.empty()) {
                    const auto next = queued_.front();
                    queued_.pop_front();
                    begin_move(next);
                }
            }
        }
    }
    int enable() { stop(); enabled_ = true; return 0; }
    int disable() { stop(); enabled_ = false; return 0; }
    int stop() { moving_ = false; queued_.clear(); hold_ = actual_; return 0; }
    void reset() {
        enabled_ = false; moving_ = false; initialized_ = false;
        queued_.clear(); outputs_.fill(0); pulse_deadline_.fill(-1);
        pulse_restore_.fill(0);
        speed_ratio_ = 100;
    }
    int mode() const { return !enabled_ ? 4 : moving_ ? 7 : 5; }
    const Joints& actual() const { return actual_; }
    int speed_factor(int ratio) {
        if (ratio < 1 || ratio > 100) return -1;
        speed_ratio_ = ratio;
        return 0;
    }
    int set_digital_output(int index, int status, int time_ms) {
        if (index < 1 || index > static_cast<int>(outputs_.size())
            || (status != 0 && status != 1) || time_ms < 0 || time_ms > 60000) return -1;
        pulse_restore_[index - 1] = outputs_[index - 1];
        outputs_[index - 1] = status;
        pulse_deadline_[index - 1] = time_ms ? now_ + time_ms / 1000. : -1;
        return 0;
    }
    int digital_output(int index) const { return outputs_.at(index - 1); }
    int move(const Joints& degrees, bool joint_mode,
             const std::vector<std::string>& params, bool linear) {
        if (!enabled_) return -3;
        // Cartesian targets and advanced firmware motion parameters require IK/trajectory planning.
        if (!joint_mode || std::any_of(params.begin(), params.end(),
                [](const auto& value) { return !value.empty(); })) return -1;
        Joints radians;
        for (int i = 0; i < 6; ++i) {
            radians[i] = degrees[i] * pi / 180.;
            if (!std::isfinite(radians[i]) || std::abs(radians[i]) > limits[i]) return -1;
        }
        if (queued_.size() >= 16) return -1;
        Move target {radians, linear};
        if (moving_) queued_.push_back(target);
        else begin_move(target);
        return 0;
    }
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
        queued_.clear();
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
    struct Move { Joints target; bool linear; };
    void begin_move(const Move& move) {
        from_ = actual_;
        target_ = move.target;
        start_time_ = now_;
        double largest_change = 0;
        for (int i = 0; i < 6; ++i)
            largest_change = std::max(largest_change, std::abs(target_[i] - from_[i]) * 180. / pi);
        const double degrees_per_second = (move.linear ? 30. : 60.) * speed_ratio_ / 100.;
        duration_ = std::max(.3, largest_change / degrees_per_second);
        moving_ = true;
    }
    bool initialized_ {false}, enabled_ {false}, moving_ {false};
    double now_ {0}, start_time_ {0}, duration_ {.1};
    int speed_ratio_ {100};
    std::deque<Move> queued_;
    std::array<int, 24> outputs_ {};
    std::array<double, 24> pulse_deadline_ {};
    std::array<int, 24> pulse_restore_ {};
    Joints actual_ {}, velocity_ {}, hold_ {}, from_ {}, target_ {};
};
}
