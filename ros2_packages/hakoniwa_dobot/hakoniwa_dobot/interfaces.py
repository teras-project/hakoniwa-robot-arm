SERVICES = ('RequestControl', 'EnableRobot', 'DisableRobot', 'ServoJ', 'MovJ',
            'MovL', 'SpeedFactor', 'DO', 'Stop',
            'GetAngle', 'RobotMode', 'ClearError', 'GetErrorID')
QUERIES = frozenset(('GetAngle', 'RobotMode', 'GetErrorID'))
DEFAULT_API = '/dobot_bringup_ros2/srv'
REAL_API = '/real/dobot_bringup_ros2/srv'
VIRTUAL_API = '/hakoniwa/dobot_bringup_ros2/srv'


def service_name(prefix, name):
    return '/' + prefix.strip('/') + '/' + name
