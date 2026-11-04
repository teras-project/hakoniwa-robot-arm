#!/usr/bin/env python3
"""Switch an already configured Nova5 ROS/TCP Launcher to the Dobot backend."""
import argparse
import json
from pathlib import Path


def adapt(data, binary, services, endpoint):
    plants = [asset for asset in data.get('assets', []) if asset.get('name') == 'nova5-plant']
    if len(plants) != 1: raise ValueError('Expected exactly one nova5-plant asset')
    plant = plants[0]
    args = plant.get('args', [])
    if '--manifest' not in args: raise ValueError('Plant manifest argument is missing')
    manifest = args[args.index('--manifest') + 1]
    plant['command'] = str(binary)
    plant['args'] = ['--manifest', manifest, '--service-config', str(services), '--rpc-endpoint', str(endpoint)]
    if '--no-viewer' in args: plant['args'].append('--no-viewer')
    data['assets'] = [a for a in data['assets'] if a.get('name') not in
                      ('nova5-trajectory-sender', 'nova5-gamepad-controller')]
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launcher', required=True, type=Path)
    p.add_argument('--binary', required=True, type=Path)
    p.add_argument('--services', required=True, type=Path)
    p.add_argument('--endpoint', required=True, type=Path)
    a = p.parse_args()
    for path in (a.launcher, a.binary, a.services, a.endpoint):
        if not path.is_file(): p.error(f'Missing file: {path}')
    original = a.launcher.read_text()
    data = adapt(json.loads(original), a.binary.resolve(), a.services.resolve(), a.endpoint.resolve())
    backup = a.launcher.with_suffix('.pre-dobot.json')
    if not backup.exists(): backup.write_text(original)
    a.launcher.write_text(json.dumps(data, indent=2) + '\n')
    print(f'Updated {a.launcher}; original saved in {backup}')

if __name__ == '__main__': main()
