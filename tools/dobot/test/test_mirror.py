"""Exercise routing semantics with executor/message stand-ins; not a ROS E2E test."""
import importlib
import json
import sys
from types import ModuleType, SimpleNamespace as NS
import pytest
from hakoniwa_dobot.interfaces import SERVICES


class Future:
    def __init__(self, **kwargs): self.value = None; self.ready = False
    def done(self): return self.ready
    def result(self): return self.value
    def set_result(self, value): self.value = value; self.ready = True
    def cancel(self): self.ready = True
    def __await__(self):
        if not self.ready: yield self
        return self.value


@pytest.fixture
def router(monkeypatch):
    modules = {}
    for name in ('rclpy', 'rclpy.node', 'rclpy.task', 'rclpy.callback_groups',
                 'std_msgs', 'std_msgs.msg', 'dobot_msgs_v4', 'dobot_msgs_v4.srv'):
        module = ModuleType(name); modules[name] = module
        monkeypatch.setitem(sys.modules, name, module)
    modules['rclpy.task'].Future = Future
    class Group: pass
    modules['rclpy.callback_groups'].ReentrantCallbackGroup = Group
    class Client:
        def __init__(self): self.ready = True; self.sent = []
        def service_is_ready(self): return self.ready
        def call_async(self, request):
            f = Future(); self.sent.append((request, f)); return f
    class Node:
        executor = None
        @property
        def clients(self): return ()
        def __init__(self, name): self.callbacks = {}; self.groups = []; self.status = []
        def create_client(self, *args): return Client()
        def create_service(self, kind, name, callback, **kwargs):
            self.callbacks[name] = callback; self.groups.append(kwargs['callback_group'])
        def create_timer(self, period, callback, **kwargs): self.groups.append(kwargs['callback_group'])
        def create_publisher(self, *args): return NS(publish=self.status.append)
        def get_logger(self): return NS(error=lambda _: None)
    modules['rclpy.node'].Node = Node
    modules['std_msgs.msg'].String = NS
    for name in SERVICES: setattr(modules['dobot_msgs_v4.srv'], name, NS)
    monkeypatch.delitem(sys.modules, 'hakoniwa_dobot.mirror', raising=False)
    m = importlib.import_module('hakoniwa_dobot.mirror')
    node = m.Mirror()
    assert all(isinstance(g, Group) for g in node.groups)  # Timer may complete an awaiting service.
    yield node
    sys.modules.pop('hakoniwa_dobot.mirror', None)


class Response:
    res = 0
    robot_return = ''
    @staticmethod
    def get_fields_and_field_types(): return {'res': 'int32', 'robot_return': 'string'}


def finish(router, name, codes):
    for client, code in zip(router._targets[name], codes):
        client.sent[-1][1].set_result(NS(res=code, robot_return='{real}'))
    router._tick()


def result(coroutine):
    with pytest.raises(StopIteration) as stopped: coroutine.send(None)
    return stopped.value.value


def test_motion_fans_out_without_changing_the_request(router):
    request = NS(a=5., param_value=['t=3'])
    call = router._callback('ServoJ')(request, Response())
    call.send(None)
    assert all(client.sent[0][0] is request for client in router._targets['ServoJ'])
    finish(router, 'ServoJ', [0, 0])
    assert result(call).res == 0


def test_query_uses_real_robot_response(router):
    call = router._callback('GetAngle')(NS(), Response())
    call.send(None)
    assert not router._targets['GetAngle'][1].sent
    finish(router, 'GetAngle', [0])
    assert result(call).robot_return == '{real}'


def test_no_motion_sent_when_either_target_is_unavailable(router):
    router._targets['ServoJ'][1].ready = False
    call = router._callback('ServoJ')(NS(), Response())
    assert result(call).res != 0
    assert all(not client.sent for client in router._targets['ServoJ'])


def test_virtual_failure_is_not_reported_as_total_success(router):
    call = router._callback('ServoJ')(NS(), Response())
    call.send(None)
    finish(router, 'ServoJ', [0, -3])
    assert result(call).res == -3


@pytest.mark.parametrize('name', ('Stop', 'DisableRobot'))
@pytest.mark.parametrize('unavailable_index', (0, 1))
def test_stopping_reaches_available_backend_and_reports_partial_failure(router, name, unavailable_index):
    clients = router._targets[name]
    clients[unavailable_index].ready = False
    request = NS()
    call = router._callback(name)(request, Response())
    call.send(None)
    available = clients[1 - unavailable_index]
    assert not clients[unavailable_index].sent
    assert available.sent[0][0] is request
    available.sent[0][1].set_result(NS(res=0, robot_return=''))
    router._tick()
    assert result(call).res != 0
    assert json.loads(router.status[-1].data)['unavailable'] == ['real' if unavailable_index == 0 else 'virtual']
