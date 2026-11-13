"""Fan out unmodified Dobot requests; queries and successful responses use the real robot."""
import argparse
import importlib
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.task import Future
from std_msgs.msg import String
from .interfaces import SERVICES, QUERIES, DEFAULT_API, REAL_API, VIRTUAL_API, service_name


class Mirror(Node):
    def __init__(self, real_prefix=REAL_API, virtual_prefix=VIRTUAL_API, api_prefix=DEFAULT_API, timeout=2.):
        super().__init__('dobot_twin_router')
        if len({real_prefix.rstrip('/'), virtual_prefix.rstrip('/'), api_prefix.rstrip('/')}) != 3:
            raise ValueError('Public, real, and virtual service prefixes must differ')
        self._callback_group = ReentrantCallbackGroup()
        self._targets = {}
        self._pending = []
        self._timeout = timeout
        self._status = self.create_publisher(String, 'dobot_twin/status', 10)
        module = importlib.import_module('dobot_msgs_v4.srv')
        for name in SERVICES:
            kind = getattr(module, name)
            self._targets[name] = (
                self.create_client(kind, service_name(real_prefix, name)),
                self.create_client(kind, service_name(virtual_prefix, name)),
            )
            self.create_service(kind, service_name(api_prefix, name), self._callback(name), callback_group=self._callback_group)
        self.create_timer(.01, self._tick, callback_group=self._callback_group)

    def _callback(self, name):
        async def callback(request, response):
            targets = self._targets[name][:1] if name in QUERIES else self._targets[name]
            ready = [client.service_is_ready() for client in targets]
            stopping = name in ('Stop', 'DisableRobot')
            if not any(ready) or (not stopping and not all(ready)):
                response.res = -1
                self.get_logger().error(f'{name}: target unavailable; nothing was sent')
                return response
            unavailable = [label for label, available in zip(('real', 'virtual'), ready) if not available]
            futures = [client.call_async(request) for client, available in zip(targets, ready) if available]
            completion = Future(executor=self.executor)
            self._pending.append((name, futures, completion, time.monotonic() + self._timeout, unavailable))
            results = await completion
            if results is not None:
                primary = results[0]
                for field in response.get_fields_and_field_types():
                    setattr(response, field, getattr(primary, field))
                if any(result.res != 0 for result in results):
                    response.res = next(result.res for result in results if result.res != 0)
            else:
                response.res = -1
            if unavailable:
                self.get_logger().error(f'{name}: partial failure; unavailable: {", ".join(unavailable)}; inspect both robots')
                if response.res == 0:
                    response.res = -1
            return response
        return callback

    def _tick(self):
        remaining = []
        for name, futures, completion, deadline, unavailable in self._pending:
            if all(f.done() for f in futures):
                try:
                    results = [f.result() for f in futures]
                    if any(r is None for r in results):
                        raise RuntimeError('Empty response')
                    status = {'service': name, 'res': [r.res for r in results]}
                    if unavailable:
                        status['unavailable'] = unavailable
                    self._status.publish(String(data=json.dumps(status)))
                    completion.set_result(results)
                except Exception as error:
                    self.get_logger().error(f'{name}: {error}; controller outcome may be unknown')
                    completion.set_result(None)
            elif time.monotonic() >= deadline:
                for f in futures:
                    if not f.done(): f.cancel()
                self.get_logger().error(f'{name}: timeout; controller outcome is unknown; inspect both robots')
                status = {'service': name, 'error': 'timeout'}
                if unavailable:
                    status['unavailable'] = unavailable
                self._status.publish(String(data=json.dumps(status)))
                completion.set_result(None)
            else:
                remaining.append((name, futures, completion, deadline, unavailable))
        self._pending = remaining


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--real-prefix', default=REAL_API)
    p.add_argument('--virtual-prefix', default=VIRTUAL_API)
    p.add_argument('--api-prefix', default=DEFAULT_API)
    from rclpy.utilities import remove_ros_args
    a = p.parse_args(remove_ros_args()[1:])
    rclpy.init()
    node = Mirror(a.real_prefix, a.virtual_prefix, a.api_prefix)
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
