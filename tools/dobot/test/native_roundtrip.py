"""Integration client for native_smoke.cpp: real TCP PDU-RPC and MuJoCo, without ROS."""
import argparse
import json
from pathlib import Path
import time
from hakoniwa_pdu_rpc import RpcClient, make_typed_client


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--library', required=True)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--endpoint', required=True)
    a = p.parse_args()
    native = json.loads(a.config.read_text())
    clients, raw = {}, []
    try:
        for service in native['services']:
            name = service['name'].split('/')[-1]
            client = RpcClient(a.library, 'dobot_ros', service['clients'][0]['name'], a.config, a.endpoint)
            raw.append(client)
            client.start()
            clients[name] = make_typed_client(client, service['name'], name,
                package='hakoniwa_pdu.pdu_msgs.dobot_msgs_v4_msgs')
        def call(name, **fields):
            client = clients[name]
            request = client.create_request()
            for key, value in fields.items(): setattr(request, key, value)
            return client.call(request, 2_000_000)
        def angle():
            response = call('GetAngle')
            assert response.res == 0
            return json.loads(response.robot_return.replace('{','[').replace('}',']'))
        assert call('RequestControl').res == 0
        assert call('ClearError').res == 0
        assert call('GetErrorID').robot_return == '{[]}'
        assert call('RobotMode').robot_return == '{4}'
        assert call('ServoJ', a=5., param_value=['t=2']).res != 0
        assert call('EnableRobot').res == 0
        assert call('ServoJ', a=5., param_value=['t=2']).res == 0
        time.sleep(.8)
        mid = angle()[0]
        assert 1. < mid < 4., mid
        assert call('Stop').res == 0
        stopped = angle()[0]
        time.sleep(.7)
        held = angle()[0]
        assert abs(held - stopped) < .2, (stopped, held)
        assert call('RobotMode').robot_return == '{5}'
        assert call('ServoJ', a=400., param_value=['t=1']).res != 0
        assert call('ServoJ', a=5., param_value=['t=.5']).res == 0
        time.sleep(1.)
        final = angle()[0]
        assert abs(final - 5.) < .15, final
        assert call('SpeedFactor', ratio=10).res == 0
        assert call('SpeedFactor', ratio=0).res != 0
        assert call('DO', index=1, status=1, time=500).res == 0
        assert call('DO', index=0, status=1, time=0).res != 0
        assert call('MovJ', mode=True, a=50., b=-8.).res == 0
        assert call('MovJ', mode=True, a=0., b=-8.).res == 0
        time.sleep(4.)
        demo_mid = angle()[0]
        assert 12. < demo_mid < 42., demo_mid
        time.sleep(18.)
        demo_final = angle()
        assert abs(demo_final[0]) < .2 and abs(demo_final[1] + 8.) < .2, demo_final
        assert call('RobotMode').robot_return == '{5}'
        assert call('MovL', mode=False).res != 0
        assert call('MovL', mode=True, a=3., b=-8.).res == 0
        time.sleep(2.)
        assert abs(angle()[0] - 3.) < .2
        assert call('DisableRobot').res == 0
        assert call('RobotMode').robot_return == '{4}'
        assert call('ServoJ', a=0., param_value=['t=1']).res != 0
        print(json.dumps({'mid_deg': mid, 'stop_deg': stopped, 'held_deg': held,
                          'final_deg': final, 'demo_mid_deg': demo_mid,
                          'demo_final_deg': demo_final, 'result': 'PASS'}, indent=2))
    finally:
        for client in raw: client.close()

if __name__ == '__main__': main()
