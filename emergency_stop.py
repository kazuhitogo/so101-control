import yaml
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE,
    ADDR_PRESENT_POSITION, ADDR_GOAL_POSITION, ADDR_TORQUE_ENABLE
)

with open('.env.yaml', 'r') as f:
    config = yaml.safe_load(f)

portHandler = PortHandler(config['follower']['port'])
packetHandler = PacketHandler(PROTOCOL_VERSION)
portHandler.openPort()
portHandler.setBaudRate(BAUDRATE)

# 全モーターの目標位置を現在位置に設定してからトルクを無効にする
for motor_name, motor_data in config['follower']['calibration'].items():
    motor_id = motor_data['id']
    
    # 現在位置を取得
    current_pos, _, _ = packetHandler.read2ByteTxRx(portHandler, motor_id, ADDR_PRESENT_POSITION)
    
    # 目標位置を現在位置に設定
    packetHandler.write2ByteTxRx(portHandler, motor_id, ADDR_GOAL_POSITION, current_pos)
    
    # トルクを無効にする
    packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
    
    print(f"{motor_name} pos={current_pos}, goal set to {current_pos}, torque disabled")

portHandler.closePort()
print("All motors stopped safely")
