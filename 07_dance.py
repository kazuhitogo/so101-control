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
    follower_port = PortHandler(config['follower']['port'])
    follower_packet = PacketHandler(PROTOCOL_VERSION)
    follower_port.openPort()
    follower_port.setBaudRate(BAUDRATE)
    
    leader_port = PortHandler(config['leader']['port'])
    leader_packet = PacketHandler(PROTOCOL_VERSION)
    leader_port.openPort()
    leader_port.setBaudRate(BAUDRATE)
    
    # モーター初期化
    for motor_name in config['follower']['calibration'].keys():
        motor_id = config['follower']['calibration'][motor_name]['id']
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_OPERATING_MODE, 0)
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_POSITION_P_GAIN, 16)
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_POSITION_I_GAIN, 0)
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_POSITION_D_GAIN, 32)
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_TORQUE_ENABLE, 1)
    
    for motor_name in config['leader']['calibration'].keys():
        motor_id = config['leader']['calibration'][motor_name]['id']
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_OPERATING_MODE, 0)
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_POSITION_P_GAIN, 16)
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_POSITION_I_GAIN, 0)
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_POSITION_D_GAIN, 32)
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_TORQUE_ENABLE, 1)
    
    # ダンス実行
    time.sleep(5)
    for step_name in dance['follower'].keys():
        print(f"実行中: {step_name}")
        for motor_name, position in dance['follower'][step_name].items():
            motor_id = config['follower']['calibration'][motor_name]['id']
            follower_packet.write2ByteTxRx(follower_port, motor_id, ADDR_GOAL_POSITION, position)
        for motor_name, position in dance['leader'][step_name].items():
            motor_id = config['leader']['calibration'][motor_name]['id']
            leader_packet.write2ByteTxRx(leader_port, motor_id, ADDR_GOAL_POSITION, position)
        time.sleep(1)
    
    # トルクOFF
    for motor_name in config['follower']['calibration'].keys():
        motor_id = config['follower']['calibration'][motor_name]['id']
        follower_packet.write1ByteTxRx(follower_port, motor_id, ADDR_TORQUE_ENABLE, 0)
    
    for motor_name in config['leader']['calibration'].keys():
        motor_id = config['leader']['calibration'][motor_name]['id']
        leader_packet.write1ByteTxRx(leader_port, motor_id, ADDR_TORQUE_ENABLE, 0)
    
    follower_port.closePort()
    leader_port.closePort()
    print("完了")

if __name__ == "__main__":
    main()
