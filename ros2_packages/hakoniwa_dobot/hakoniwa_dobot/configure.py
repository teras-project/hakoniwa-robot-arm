"""Generate Service Bridge/RPC config from this package's explicit Dobot API subset."""
import argparse
import json
from pathlib import Path
from .interfaces import SERVICES, VIRTUAL_API, service_name


def write_binding(output, prefix=VIRTUAL_API, address='127.0.0.1', port=54020):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    transport = {'protocol': 'tcp', 'packetVersion': 'v2', 'queueDepth': 16, 'endpoints': {
        'dobot_ros': {'role': 'client', 'remote': {'address': address, 'port': port},
                      'options': {'connect_timeout_ms': 2000, 'read_timeout_ms': 0, 'write_timeout_ms': 1000}},
        'dobot_virtual': {'role': 'server', 'local': {'address': '0.0.0.0', 'port': port},
                      'options': {'read_timeout_ms': 0, 'write_timeout_ms': 1000}},
    }}
    (output / 'transport.json').write_text(json.dumps(transport, indent=2) + '\n')
    binding = {'version': 1, 'service': {'transport_config': 'transport.json'}, 'bindings': [
        {'ros_name': service_name(prefix, name), 'ros_type': f'dobot_msgs_v4/srv/{name}',
         'hakoniwa_service': f'Dobot/{name}', 'pdu_service_type': f'dobot_msgs_v4_msgs/{name}',
         'client_endpoint': {'node_id': 'dobot_ros'}, 'server_endpoint': {'node_id': 'dobot_virtual'},
         'max_clients': 1, 'timeout_msec': 2000,
         'heap': {'request_bytes': 1024, 'response_bytes': 1024}}
        for name in SERVICES]}
    path = output / 'dobot-services.json'
    path.write_text(json.dumps(binding, indent=2) + '\n')
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--prefix', default=VIRTUAL_API)
    p.add_argument('--address', default='127.0.0.1')
    p.add_argument('--port', type=int, default=54020)
    p.add_argument('--offset-dir', required=True, type=Path)
    a = p.parse_args()
    if not 1 <= a.port <= 65535: p.error('port must be 1..65535')
    binding = write_binding(a.output, a.prefix, a.address, a.port)
    from hakoniwa_pdu_ros.generate_service_config import generate_service_configs
    generated = generate_service_configs(binding, output_dir=a.output / 'rpc', offset_dir=a.offset_dir)
    print(f'Binding: {binding}')
    print(f'Native services: {generated.server_config}')
    print(f'Native server endpoint: {generated.output_dir / "endpoints/dobot_virtual.json"}')
    print(f'ROS client endpoints: {generated.endpoint_config}')

if __name__ == '__main__': main()
