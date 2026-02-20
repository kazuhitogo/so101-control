#!/usr/bin/env python3
import yaml
import time
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE,
    ADDR_TORQUE_ENABLE, ADDR_GOAL_POSITION,
    ADDR_POSITION_P_GAIN, ADDR_POSITION_I_GAIN, ADDR_POSITION_D_GAIN, 
    ADDR_OPERATING_MODE,
)

def main():
    # 設定ファイル読み込み
    with open('.env.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('dance.yaml', 'r') as f:
        dance = yaml.safe_load(f)
    
    # ポート接続
    portHandler = PortHandler(config['follower']['port'])
    packetHandler = PacketHandler(PROTOCOL_VERSION)
    portHandler.openPort()
    portHandler.setBaudRate(BAUDRATE)
    
    # モーター初期化
    for motor_name in config['follower']['calibration'].keys():
        motor_id = config['follower']['calibration'][motor_name]['id']
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_OPERATING_MODE, 0)
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_POSITION_P_GAIN, 16)
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_POSITION_I_GAIN, 0)
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_POSITION_D_GAIN, 32)
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 1)
    
    # ダンス実行
    for step_name, positions in dance['follower'].items():
        print(f"実行中: {step_name}")
        for motor_name, position in positions.items():
            motor_id = config['follower']['calibration'][motor_name]['id']
            packetHandler.write2ByteTxRx(portHandler, motor_id, ADDR_GOAL_POSITION, position)
        time.sleep(1)
    
    # トルクOFF
    for motor_name in config['follower']['calibration'].keys():
        motor_id = config['follower']['calibration'][motor_name]['id']
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
    
    portHandler.closePort()
    print("完了")

if __name__ == "__main__":
    main()
