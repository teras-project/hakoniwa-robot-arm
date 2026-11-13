import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from hakoniwa_dobot.interfaces import DEFAULT_API, SERVICES, VIRTUAL_API, service_name


def load_launch(monkeypatch):
    launch = ModuleType('launch')
    actions = ModuleType('launch.actions')
    substitutions = ModuleType('launch.substitutions')
    launch_ros = ModuleType('launch_ros')
    ros_actions = ModuleType('launch_ros.actions')

    class LaunchConfiguration:
        def __init__(self, name):
            self.name = name

        def perform(self, context):
            return context[self.name]

    launch.LaunchDescription = lambda entries: entries
    actions.DeclareLaunchArgument = lambda name, **kwargs: SimpleNamespace(name=name, **kwargs)
    actions.OpaqueFunction = lambda **kwargs: kwargs
    substitutions.LaunchConfiguration = LaunchConfiguration
    ros_actions.Node = lambda **kwargs: SimpleNamespace(**kwargs)
    for name, module in (
        ('launch', launch),
        ('launch.actions', actions),
        ('launch.substitutions', substitutions),
        ('launch_ros', launch_ros),
        ('launch_ros.actions', ros_actions),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    path = Path(__file__).resolve().parents[3] / 'ros2_packages/hakoniwa_dobot/launch/dobot.launch.py'
    spec = importlib.util.spec_from_file_location('dobot_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_virtual_mode_publishes_official_api_without_real_driver(monkeypatch):
    module = load_launch(monkeypatch)
    backend = module.generate_launch_description()[0]
    assert backend.name == 'backend'
    assert backend.default_value == 'virtual'
    assert backend.choices == ['real', 'virtual', 'both']

    nodes = module.setup({
        'backend': 'virtual', 'api_prefix': DEFAULT_API, 'service_binding': 'services.json',
        'offset_dir': 'offset', 'rpc_output': 'rpc', 'topic_binding': 'topic.json',
    })
    assert [node.name for node in nodes] == ['dobot_virtual_services', 'dobot_virtual_topics']
    assert nodes[0].remappings == [
        (service_name(VIRTUAL_API, name), service_name(DEFAULT_API, name)) for name in SERVICES
    ]
    assert nodes[1].remappings == [('/pdu/joint_states', '/joint_states_robot')]


def test_both_mode_separates_driver_and_virtual_services(monkeypatch):
    module = load_launch(monkeypatch)
    nodes = module.setup({
        'backend': 'both', 'api_prefix': DEFAULT_API, 'robot_ip': '192.0.2.1',
        'service_binding': 'services.json', 'offset_dir': 'offset',
        'rpc_output': 'rpc', 'topic_binding': 'topic.json',
    })
    assert [node.name for node in nodes[:3]] == [
        'dobot_real_driver', 'dobot_virtual_services', 'dobot_virtual_topics'
    ]
    assert nodes[0].remappings[0] == (
        service_name(DEFAULT_API, SERVICES[0]), service_name('/real/dobot_bringup_ros2/srv', SERVICES[0])
    )
    assert nodes[1].remappings[0] == (service_name(VIRTUAL_API, SERVICES[0]), service_name(VIRTUAL_API, SERVICES[0]))
    assert nodes[2].remappings == [('/pdu/joint_states', '/hakoniwa/joint_states_robot')]
    assert nodes[3].executable == 'mirror'
