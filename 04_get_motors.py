#!/usr/bin/env python3
# モーター位置取得スクリプト

import yaml
import time
from scservo_sdk import *
from servo_constants import *

def main():
    # 設定ファイル読み込み
    with open('.env.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # ポート接続
    portHandler = PortHandler(config['follower']['port'])
    packetHandler = PacketHandler(PROTOCOL_VERSION)
    portHandler.openPort()
    portHandler.setBaudRate(BAUDRATE)

    try:
        # グリッパーの現在位置を取得
        gripper_id = config['follower']['calibration']['gripper']['id']
        
        # Operating Mode を Position に設定
        packetHandler.write1ByteTxRx(portHandler, gripper_id, 33, 0)  # Operating_Mode = 0 (Position)
        
        # トルクを有効にする
        packetHandler.write1ByteTxRx(portHandler, gripper_id, ADDR_TORQUE_ENABLE, 1)
        
        current_pos, _, _ = packetHandler.read2ByteTxRx(portHandler, gripper_id, ADDR_PRESENT_POSITION)
        print(f"gripper current: {current_pos}")
        
        # 1秒後に +10
        time.sleep(1)
        packetHandler.write2ByteTxRx(portHandler, gripper_id, ADDR_GOAL_POSITION, current_pos + 10)
        print(f"gripper moved to: {current_pos + 10}")
        
        # さらに1秒後に -10
        time.sleep(1)
        packetHandler.write2ByteTxRx(portHandler, gripper_id, ADDR_GOAL_POSITION, current_pos - 10)
        print(f"gripper moved to: {current_pos - 10}")
        
        # 1秒待ってからトルクを無効にする
        time.sleep(1)
        packetHandler.write1ByteTxRx(portHandler, gripper_id, ADDR_TORQUE_ENABLE, 0)
        print("gripper torque disabled")
        
    finally:
        # 処理が途中で止まってもトルクを無効化
        for motor_name, motor_data in config['follower']['calibration'].items():
            packetHandler.write1ByteTxRx(portHandler, motor_data['id'], ADDR_TORQUE_ENABLE, 0)
        # ポート閉じる
        portHandler.closePort()

if __name__ == "__main__":
    main()
