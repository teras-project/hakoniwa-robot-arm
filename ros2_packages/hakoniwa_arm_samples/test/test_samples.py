import sys
from types import SimpleNamespace

import pytest
from sensor_msgs.msg import JointState

from hakoniwa_arm_samples import control, monitor


def test_official_get_angle_format_rejects_bad_readings():
    assert control.parse_angles("{0, -8, 0, 0, 0, 0}") == [0, -8, 0, 0, 0, 0]
    for bad in ("0, -8, 0, 0, 0, 0", "{}", "{nan, 0, 0, 0, 0, 0}", "{1, 2}"):
        with pytest.raises(ValueError):
            control.parse_angles(bad)


def test_monitor_uses_official_topic_and_logs_once_per_second(monkeypatch):
    logs = []
    clock = iter((0., .5, 1., 1.4, 2.1))

    class FakeNode:
        def __init__(self, _name):
            pass

        def create_subscription(self, _kind, topic, callback, _qos):
            assert topic == "/joint_states_robot"
            self.callback = callback

        def get_logger(self):
            return SimpleNamespace(info=logs.append)

        def destroy_node(self):
            pass

    def spin(node):
        state = JointState()
        state.name = ["joint1"]
        state.position = [0.5]
        for _ in range(5):
            node.callback(state)

    monkeypatch.setattr(monitor, "Node", FakeNode)
    monkeypatch.setattr(monitor, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    monkeypatch.setattr(monitor.rclpy, "init", lambda: None)
    monkeypatch.setattr(monitor.rclpy, "spin", spin)
    monkeypatch.setattr(monitor.rclpy, "ok", lambda: False)
    monkeypatch.setattr(sys, "argv", ["monitor"])
    monitor.main()
    assert logs == [
        "monitoring /joint_states_robot",
        "joint1=0.500",
        "joint1=0.500",
        "joint1=0.500",
    ]
