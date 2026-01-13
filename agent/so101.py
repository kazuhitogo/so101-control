from mcp.server.fastmcp import FastMCP
import yaml
import sys
import os
import signal
import atexit

# パッケージのルートディレクトリをパスに追加
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE,
    ADDR_TORQUE_ENABLE, ADDR_PRESENT_POSITION, ADDR_GOAL_POSITION,
    ADDR_POSITION_P_GAIN, ADDR_POSITION_I_GAIN, ADDR_POSITION_D_GAIN, 
    ADDR_OPERATING_MODE,
)
from scservo_sdk import PortHandler, PacketHandler
from time import sleep

class Motor():
    def __init__(self, portHandler, packetHandler, motor_id, motor_name, range_min, range_max):
        self.portHandler = portHandler
        self.packetHandler = packetHandler
        self.motor_id = motor_id
        self.motor_name = motor_name
        self.p_gain = self.set_parameter(ADDR_POSITION_P_GAIN,16)
        self.i_gain = self.set_parameter(ADDR_POSITION_I_GAIN,0)
        self.d_gain = self.set_parameter(ADDR_POSITION_D_GAIN,32)
        self.range_min = range_min
        self.range_max = range_max
        self.torque_enable = self.set_parameter(ADDR_TORQUE_ENABLE, 1)
        self.operating_mode = self.set_parameter(ADDR_OPERATING_MODE, 0)
        self.position = self.get_paramter(ADDR_PRESENT_POSITION)
    
    def validate_goal_position(self, position):
        if self.range_min <= position <= self.range_max:
            return True
        else:
            return False
    
    def set_goal_position(self, position):
        if self.validate_goal_position(position):
            self.set_parameter(ADDR_GOAL_POSITION,position)
            return True
        else:
            return False
    
    def get_current_position(self):
        self.position = self.get_paramter(ADDR_PRESENT_POSITION)
        return self.position
    
    def set_parameter(self, address, parameter):
        self.packetHandler.write2ByteTxRx(self.portHandler, self.motor_id, address, parameter)
        return parameter
    
    def get_paramter(self, address):
        return self.packetHandler.read2ByteTxRx(self.portHandler, self.motor_id, address)
    
    def disable_torque(self):
        self.set_parameter(ADDR_TORQUE_ENABLE, 0)

class So101():
    def __init__(self, env_file=".env.yaml"):
        with open(env_file, 'r') as f:
            self.config = yaml.safe_load(f)
        self.portHandler = PortHandler(self.config['follower']['port'])
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)
        self.portHandler.openPort()
        self.portHandler.setBaudRate(BAUDRATE)
        self.motors = [
            Motor(
                self.portHandler,
                self.packetHandler,
                self.config['follower']['calibration'][motor_name]['id'],
                motor_name,
                self.config['follower']['calibration'][motor_name]["range_min"],
                self.config['follower']['calibration'][motor_name]["range_max"],
            ) for motor_name in sorted(self.config['follower']['calibration'].keys(),key=lambda motor_name: self.config['follower']['calibration'][motor_name]['id'])
        ]
        self.motors = {}
        self.set_motors()
        
        # クリーンアップ処理を登録
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        try:
            for motor in self.motors.values():
                motor.disable_torque()
            self.portHandler.closePort()
        except:
            pass

    def set_motors(self):
        for motor_name in sorted(self.config['follower']['calibration'].keys(),key=lambda motor_name: self.config['follower']['calibration'][motor_name]['id']):
            self.motors[motor_name] = Motor(
                self.portHandler,
                self.packetHandler,
                self.config['follower']['calibration'][motor_name]['id'],
                motor_name,
                self.config['follower']['calibration'][motor_name]["range_min"],
                self.config['follower']['calibration'][motor_name]["range_max"],
            )

    def __del__(self):
        self.cleanup()


so101 = So101()

mcp = FastMCP("SO101")

@mcp.tool()
def set_motors_position(motor_position_dict):
    """
    ロボットアームのすべてのモーターを同時に指定位置に移動させる
    
    Args:
        motor_position_dict (dict): モーター名をキー、目標位置を値とする辞書。
        動かさないモーターは省略可。値は 0-4095 までだがモーターごとに可動範囲の制約があり 0-4095 でも設定できない場合がある。
        設定できない値の場合はエラーメッセージで設定できる値の範囲を返す。
        以下はすべてのモーターを動かす例: 
        {
            "shoulder_pan": 2048,
            "shoulder_lift": 2048,
            "elbow_flex": 2048,
            "wrist_flex": 2048,
            "wrist_roll": 2048,
            "gripper": 2048
        }
    
    Returns:
        dict or list: 成功時は各モーターの現在位置を含む辞書、
                     失敗時は範囲外エラーメッセージのリスト
    """
    errors = []
    enable = True
    for motor in motor_position_dict.keys():
        enable *= so101.motors[motor].validate_goal_position(motor_position_dict[motor])
        if enable:
            pass
        else:
            errors.append(f"{motor} は {so101.motors[motor].range_min} から {so101.motors[motor].range_max} の値以外許されません")
    
    if enable:
        for motor in motor_position_dict.keys():
            so101.motors[motor].set_goal_position(motor_position_dict[motor])
        sleep(1)
        result = {}
        for motor in motor_position_dict.keys():
            result[motor] = so101.motors[motor].get_current_position()
        return result

    else:
        return errors

@mcp.tool()
def get_motors_position():
    """
    ロボットアームのすべてのモーターの現在位置を取得する

    Args:
        None

    Returns:
        dict: モーター名をキー、現在位置を値とする辞書
              例: {
                  "shoulder_pan": 2048,
                  "shoulder_lift": 2048,
                  "elbow_flex": 2048,
                  "wrist_flex": 2048,
                  "wrist_roll": 2048,
                  "gripper": 2048
              }
    """
    result = {}
    for motor in so101.motors.keys():
        result[motor] = so101.motors[motor].get_current_position()
    return result
    
if __name__ == "__main__":
    mcp.run(transport="stdio")
    