from mcp.server.fastmcp import FastMCP
import yaml
import sys
import signal
import atexit

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
    def __init__(self, arm, env_file=".env.yaml"):
        with open(env_file, "r") as f:
            self.config = yaml.safe_load(f)
        self.portHandler = PortHandler(self.config[arm]["port"])
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)
        self.portHandler.openPort()
        self.portHandler.setBaudRate(BAUDRATE)
        self.motors = [
            Motor(
                self.portHandler,
                self.packetHandler,
                self.config[arm]["calibration"][motor_name]["id"],
                motor_name,
                self.config[arm]["calibration"][motor_name]["range_min"],
                self.config[arm]["calibration"][motor_name]["range_max"],
            ) for motor_name in sorted(self.config[arm]["calibration"].keys(),key=lambda motor_name: self.config[arm]["calibration"][motor_name]["id"])
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
        except Exception:
            pass

    def set_motors(self):
        for motor_name in sorted(self.config[arm]["calibration"].keys(),key=lambda motor_name: self.config[arm]["calibration"][motor_name]["id"]):
            self.motors[motor_name] = Motor(
                self.portHandler,
                self.packetHandler,
                self.config[arm]["calibration"][motor_name]["id"],
                motor_name,
                self.config[arm]["calibration"][motor_name]["range_min"],
                self.config[arm]["calibration"][motor_name]["range_max"],
            )

    def __del__(self):
        self.cleanup()


so101 = So101()

