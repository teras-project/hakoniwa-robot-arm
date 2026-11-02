"""Send one small absolute ServoJ target derived from GetAngle; no automatic enable."""
import argparse
import json
import math
import rclpy
from rclpy.node import Node
from dobot_msgs_v4.srv import GetAngle, RobotMode, ServoJ
from .interfaces import DEFAULT_API, service_name


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--joint', type=int, choices=range(1, 7), default=1)
    p.add_argument('--delta-deg', type=float, default=5.)
    p.add_argument('--duration', type=float, default=3.)
    p.add_argument('--api-prefix', default=DEFAULT_API)
    p.add_argument('--execute', action='store_true', help='actually send the motion request')
    from rclpy.utilities import remove_ros_args
    a = p.parse_args(remove_ros_args()[1:])
    if not math.isfinite(a.delta_deg) or abs(a.delta_deg) > 5: p.error('delta-deg must be within -5..5')
    if not math.isfinite(a.duration) or not .1 <= a.duration <= 120: p.error('duration must be 0.1..120 seconds')
    rclpy.init()
    node = Node('dobot_small_joint_sample')
    try:
        def call(kind, request=None):
            client = node.create_client(kind, service_name(a.api_prefix, kind.__name__))
            if not client.wait_for_service(timeout_sec=5.): raise RuntimeError(f'{kind.__name__} unavailable')
            future = client.call_async(request if request is not None else kind.Request())
            rclpy.spin_until_future_complete(node, future, timeout_sec=3.)
            if not future.done(): raise RuntimeError(f'{kind.__name__} timeout; outcome unknown')
            response = future.result()
            node.destroy_client(client)
            if response is None or response.res != 0: raise RuntimeError(f'{kind.__name__} failed: {response}')
            return response
        text = call(GetAngle).robot_return
        angles = json.loads(text.replace('{', '[').replace('}', ']'))
        if len(angles) != 6 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in angles):
            raise RuntimeError('Invalid GetAngle response')
        target = list(angles)
        target[a.joint - 1] += a.delta_deg
        print(f'Current deg: {angles}\nTarget deg:  {target}\nDuration: {a.duration}s')
        if not a.execute:
            print('Dry-run; no motion command sent. Add --execute to send ServoJ.')
            return
        if call(RobotMode).robot_return.strip() != '{5}':
            raise RuntimeError('Robot must already be enabled and idle (RobotMode=5)')
        request = ServoJ.Request()
        for field, value in zip('abcdef', target): setattr(request, field, float(value))
        request.param_value = [f't={a.duration}']
        call(ServoJ, request)
        print('ServoJ accepted. Observe GetAngle/JointState; this is not an arrival check.')
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == '__main__': main()
