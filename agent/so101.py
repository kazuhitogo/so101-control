import yaml
import sys
import os

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
    
    def set_goal_position(self, position):
        if self.range_min <= position <= self.range_max:
            self.packetHandler.write2ByteTxRx(self.portHandler, self.motor_id, ADDR_GOAL_POSITION, position)
            sleep(1)
            self.position = self.get_paramter(ADDR_PRESENT_POSITION)
            return f"{self.motor_name} を {self.position} に動かしました"
        else:
            return f"{self.motor_name} は {self.range_min} から {self.range_max} の値が許されています"
    
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
        for motor in self.motors.keys():
            self.motors[motor].disable_torque()
        self.portHandler.closePort()


# so101 = So101()

@mcp.tool()
def set_position(motor_name, position):
    pass

if __name__ == "__main__":
    so101 = So101()
    print(so101.motors["gripper"].set_goal_position(2048))


