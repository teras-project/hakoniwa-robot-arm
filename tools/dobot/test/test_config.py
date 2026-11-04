import importlib.util
import json
from pathlib import Path
import pytest
from hakoniwa_dobot.configure import write_binding
from hakoniwa_dobot.interfaces import SERVICES


def test_binding_uses_official_types_and_bounded_rpc(tmp_path):
    path = write_binding(tmp_path)
    binding = json.loads(path.read_text())
    assert {b['ros_type'] for b in binding['bindings']} == {f'dobot_msgs_v4/srv/{n}' for n in SERVICES}
    assert all(b['ros_name'].startswith('/hakoniwa/dobot_bringup_ros2/srv/') for b in binding['bindings'])
    assert all(b['server_endpoint']['node_id'] == 'dobot_virtual' for b in binding['bindings'])
    assert 'dobot_virtual' in json.loads((tmp_path / 'transport.json').read_text())['endpoints']
    assert all(b['max_clients'] == 1 and b['timeout_msec'] == 2000 for b in binding['bindings'])


def test_launcher_adaptation_preserves_manifest_bridge_and_original(tmp_path):
    module_path = Path(__file__).resolve().parents[1] / 'adapt_launcher.py'
    spec = importlib.util.spec_from_file_location('adapt', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = {'assets': [
        {'name': 'nova5-plant', 'command': 'old', 'args': ['--manifest', 'model.json', '--no-viewer']},
        {'name': 'nova5-trajectory-sender'}, {'name': 'nova5-ros2-tcp-bridge', 'args': ['bridge.json']}]}
    result = module.adapt(data, Path('/new'), Path('/services'), Path('/endpoint'))
    assert [a['name'] for a in result['assets']] == ['nova5-plant', 'nova5-ros2-tcp-bridge']
    assert result['assets'][0]['args'][:2] == ['--manifest', 'model.json']
    assert '--no-viewer' in result['assets'][0]['args']
    assert result['assets'][1]['args'] == ['bridge.json']


def test_invalid_launcher_rejected():
    spec = importlib.util.spec_from_file_location('adapt', Path(__file__).resolve().parents[1] / 'adapt_launcher.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError): module.adapt({'assets': []}, Path('a'), Path('b'), Path('c'))
