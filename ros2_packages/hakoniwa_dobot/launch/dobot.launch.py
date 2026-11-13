"""Official driver + optional Hakoniwa Service Bridge, selected without changing user API."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from hakoniwa_dobot.interfaces import SERVICES, DEFAULT_API, REAL_API, VIRTUAL_API, service_name


def setup(context):
    get = lambda name: LaunchConfiguration(name).perform(context)
    mode = get('backend')
    api = get('api_prefix')
    actions = []
    if mode in ('real', 'both'):
        ip = get('robot_ip')
        if not ip: raise ValueError('robot_ip must explicitly identify the real robot')
        target = REAL_API if mode == 'both' else api
        state_topic = '/real/joint_states_robot' if mode == 'both' else '/joint_states_robot'
        remaps = [(service_name(DEFAULT_API, n), service_name(target, n)) for n in SERVICES]
        remaps += [('/joint_states_robot', state_topic)]
        actions.append(Node(package='dobot_bringup_v4', executable='dobot_bringup_v4_node',
            name='dobot_real_driver', output='screen', parameters=[{
                'robot_ip_address': ip, 'robot_type': 'nova5', 'robot_node_name': 'dobot_bringup_ros2',
                'robot_number': 1, 'trajectory_duration': .3}], remappings=remaps))
    if mode in ('virtual', 'both'):
        # Binding defaults to VIRTUAL_API. Remapping also supports other configured source prefixes.
        binding = get('service_binding')
        offsets = get('offset_dir')
        if not binding or not offsets: raise ValueError('service_binding and offset_dir are required for virtual mode')
        target = VIRTUAL_API if mode == 'both' else api
        remaps = [(service_name(VIRTUAL_API, n), service_name(target, n)) for n in SERVICES]
        actions.append(Node(package='hakoniwa_pdu_ros', executable='service-server',
            name='dobot_virtual_services', output='screen', arguments=['--config', binding,
                '--offset-dir', offsets, '--output-dir', get('rpc_output')], remappings=remaps))
    if mode in ('virtual', 'both') and get('topic_binding'):
        state_topic = '/hakoniwa/joint_states_robot' if mode == 'both' else '/joint_states_robot'
        actions.append(Node(package='hakoniwa_pdu_ros', executable='bridge',
            name='dobot_virtual_topics', output='screen', arguments=['--config', get('topic_binding')],
            remappings=[('/pdu/joint_states', state_topic)]))
    if mode == 'both':
        actions.append(Node(package='hakoniwa_dobot', executable='mirror', output='screen',
            arguments=['--api-prefix', api]))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='virtual', choices=['real', 'virtual', 'both']),
        DeclareLaunchArgument('robot_ip', default_value=''),
        DeclareLaunchArgument('api_prefix', default_value=DEFAULT_API),
        DeclareLaunchArgument('service_binding', default_value=''),
        DeclareLaunchArgument('offset_dir', default_value=''),
        DeclareLaunchArgument('topic_binding', default_value=''),
        DeclareLaunchArgument('rpc_output', default_value='/tmp/hakoniwa-dobot-rpc'),
        OpaqueFunction(function=setup),
    ])
