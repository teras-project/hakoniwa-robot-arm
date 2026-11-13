#!/usr/bin/env python3
"""Start the headless-only harness and exercise real TCP/PDU-RPC + MuJoCo."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server', required=True, type=Path)
    p.add_argument('--config-root', required=True, type=Path, help='Generated RPC output directory')
    p.add_argument('--library', default=os.environ.get('HAKO_PDU_RPC_LIBRARY'))
    p.add_argument('--port', type=int, default=54020)
    a = p.parse_args()
    if not a.library: p.error('Provide --library or HAKO_PDU_RPC_LIBRARY')
    root = a.config_root.resolve()
    with tempfile.TemporaryFile(mode='w+') as log:
        server = subprocess.Popen([str(a.server.resolve()), str(root / 'rpc-server-services.json'),
            str(root / 'endpoints/dobot_virtual.json')], stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 5.
            while True:
                if server.poll() is not None: raise RuntimeError('Headless server exited before startup')
                try:
                    with socket.create_connection(('127.0.0.1', a.port), timeout=.1): break
                except OSError:
                    if time.monotonic() > deadline: raise
                    time.sleep(.05)
            client = Path(__file__).parent / 'test/native_roundtrip.py'
            result = subprocess.run([sys.executable, str(client), '--library', a.library,
                '--config', str(root / 'rpc-client-services.json'), '--endpoint', str(root / 'endpoints.json')],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40.)
            print(result.stdout[-4000:])
            if result.returncode: raise RuntimeError('Native roundtrip failed')
        except Exception:
            log.seek(0); print(log.read()[-4000:], file=sys.stderr)
            raise
        finally:
            server.terminate()
            server.wait(timeout=5.)

if __name__ == '__main__': main()
