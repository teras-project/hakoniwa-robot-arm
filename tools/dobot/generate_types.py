#!/usr/bin/env python3
"""Generate a private PDU overlay from the actual Dobot .srv sources (no copies maintained)."""
import argparse
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

SERVICES = ('RequestControl', 'EnableRobot', 'DisableRobot', 'ServoJ', 'MovJ',
            'MovL', 'SpeedFactor', 'DO', 'Stop',
            'GetAngle', 'RobotMode', 'ClearError', 'GetErrorID')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dobot-src', required=True, type=Path)
    p.add_argument('--registry', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    registry, output = a.registry.resolve(), a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    srv_dir = output / 'srv/dobot_msgs_v4'
    srv_dir.mkdir(parents=True, exist_ok=True)
    for name in SERVICES:
        shutil.copyfile(a.dobot_src / 'dobot_msgs_v4/srv' / (name + '.srv'), srv_dir / (name + '.srv'))
        subprocess.run([sys.executable, '-m', 'generators.generate_hako_service_msgs.main',
                        str(srv_dir / (name + '.srv')), '--out', str(output / 'idl')], cwd=registry, check=True)
    messages = output / 'messages.txt'
    messages.write_text(''.join(f'dobot_msgs_v4_msgs/{n}{kind}Packet\n' for n in SERVICES for kind in ('Request', 'Response')))
    paths = output / 'search.txt'
    paths.write_text(str(output / 'idl') + '\n' + str(registry / 'idl') + '\n')
    includes = output / 'includes.txt'
    includes.write_text(str(registry / 'pdu/types') + '\n')
    subprocess.run([sys.executable, '-m', 'generators.generate_hako_pdu_msgs.main', str(messages),
                    '--search-path-file', str(paths), '--output-dir', str(output / 'pdu'),
                    '--template-dir', str(registry / 'template'), '--offset-include-path-file', str(includes)],
                   cwd=registry, check=True)
    # Package overlay: adding this root to PYTHONPATH extends generated PDU modules.
    package = output / 'python/hakoniwa_pdu/pdu_msgs'
    package.mkdir(parents=True, exist_ok=True)
    for directory in (package.parent, package):
        (directory / '__init__.py').write_text('from pkgutil import extend_path\n__path__ = extend_path(__path__, __name__)\n')
    shutil.copytree(output / 'pdu/python/dobot_msgs_v4_msgs', package / 'dobot_msgs_v4_msgs', dirs_exist_ok=True)
    # Validate all expected artifacts; a generator warning must not become a successful setup.
    for name in SERVICES:
        for kind in ('Request', 'Response'):
            assert (output / f'pdu/types/dobot_msgs_v4_msgs/pdu_cpptype_conv_{name}{kind}Packet.hpp').is_file()
            assert (output / f'pdu/offset/dobot_msgs_v4_msgs/{name}{kind}Packet.offset').is_file()
    (output / 'activate.bash').write_text(
        'export HAKO_DOBOT_PDU_DIR=' + shlex.quote(str(output)) + '\n' +
        'export PYTHONPATH=' + shlex.quote(str(output / 'python')) + '${PYTHONPATH:+:$PYTHONPATH}\n')
    print(f'PDU overlay ready: {output}')

if __name__ == '__main__': main()
