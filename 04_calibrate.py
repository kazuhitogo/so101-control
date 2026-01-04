#!/usr/bin/env python3

import time
import yaml
import select
import sys
import scservo_sdk as scs
from servo_constants import *

def load_config():
    """設定を.env.yamlから読み込み"""
    with open('.env.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config

def save_config(config):
    """設定を.env.yamlに保存"""
    with open('.env.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)

def main():
    print("SO101 フォロワーアーム キャリブレーション")
    print("=" * 40)
    
    # 1. .env.yamlから設定を読み込み
    config = load_config()
    port = config['follower']['port']
    robot_id = "my_first_follower_arm"  # .env.yaml構造から
    
    # 2. FeetechMotorsBus相当の初期化
    port_handler = scs.PortHandler(port)
    packet_handler = scs.PacketHandler(PROTOCOL_VERSION)
    
    # 3. ポートに接続
    if not port_handler.openPort():
        print(f"ポート {port} のオープンに失敗しました")
        return
    
    if not port_handler.setBaudRate(BAUDRATE):
        print(f"ボーレート {BAUDRATE} の設定に失敗しました")
        return
    
    print(f"{port} に接続しました")
    
    # 4. キャリブレーションの存在確認 (SO101Follower.calibrate()相当)
    existing_calibration = config.get('follower', {}).get('calibration', {})
    
    if existing_calibration:
        user_input = input(
            f"ENTERを押すとID {robot_id} に関連付けられた既存のキャリブレーションファイルを使用します。"
            f"'c'を入力してENTERを押すとキャリブレーションを実行します: "
        )
        if user_input.strip().lower() != "c":
            print(f"ID {robot_id} に関連付けられたキャリブレーションファイルをモーターに書き込み中")
            # 既存のキャリブレーションをモーターに書き込み
            for motor_name, motor_id in SO101_MOTORS.items():
                if motor_name in existing_calibration:
                    cal = existing_calibration[motor_name]
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 31, cal['homing_offset'])  # Homing_Offset
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 6, cal['range_min'])       # Min_Position_Limit
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 8, cal['range_max'])       # Max_Position_Limit
            print("キャリブレーションをモーターに書き込みました")
            port_handler.closePort()
            return
    
    print(f"\nSO101 フォロワーのキャリブレーションを実行中")
    
    # 5. トルクを無効化 (self.bus.disable_torque()相当)
    for motor_name, motor_id in SO101_MOTORS.items():
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)  # Torque_Enable = 0
        packet_handler.write1ByteTxRx(port_handler, motor_id, 55, 0)                  # Lock = 0
    
    # 6. 動作モードをポジションに設定 (OperatingMode.POSITION.value相当)
    for motor_name, motor_id in SO101_MOTORS.items():
        packet_handler.write1ByteTxRx(port_handler, motor_id, 33, 0)  # Operating_Mode = 0 (POSITION)
    
    # 7. 各モーターを個別にキャリブレーション (ID順: 中央値→min→max→次のモーター)
    homing_offsets = {}
    range_mins = {}
    range_maxes = {}
    
    for motor_name, motor_id in sorted(SO101_MOTORS.items(), key=lambda x: x[1]):  # ID順でソート
        print(f"\n=== {motor_name} (ID: {motor_id}) キャリブレーション開始 ===")
        
        # ステップ1: 中央位置設定（ホーミングオフセット）
        print(f"\n--- ステップ1: {motor_name} 中央位置設定 ---")
        while True:
            present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            
            # 画面をクリアして現在のモーター位置を表示
            print("\033[2J\033[H", end="")  # 画面クリア
            print(f"SO101 フォロワー キャリブレーション - {motor_name} (ID: {motor_id})")
            print("=" * 50)
            print("ステップ1: 中央位置設定")
            print(f"現在位置: {present_pos}")
            print(f"\n{motor_name} を可動範囲の中央に移動してENTERを押してください...")
            
            # ユーザー入力をチェック (ノンブロッキング)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                input()  # 入力を消費
                break
            
            time.sleep(0.1)
        
        # ホーミングオフセットを計算・設定
        present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        homing_offset = present_pos - 2047
        homing_offsets[motor_name] = homing_offset
        packet_handler.write2ByteTxRx(port_handler, motor_id, 31, homing_offset)  # Homing_Offset
        print(f"{motor_name}: ホーミングオフセット = {homing_offset} 設定完了")
        
        # ステップ2: 最小値探索
        print(f"\n--- ステップ2: {motor_name} 最小値探索 ---")
        present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        range_mins[motor_name] = present_pos
        
        while True:
            present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            range_mins[motor_name] = min(range_mins[motor_name], present_pos)
            
            # 画面をクリアして最小値探索状況を表示
            print("\033[2J\033[H", end="")  # 画面クリア
            print(f"SO101 フォロワー キャリブレーション - {motor_name} (ID: {motor_id})")
            print("=" * 50)
            print("ステップ2: 最小値探索")
            print(f"現在位置: {present_pos}")
            print(f"記録最小値: {range_mins[motor_name]}")
            print(f"\n{motor_name} を最小位置まで動かし、完了したらENTERを押してください...")
            
            # ユーザー入力をチェック (ノンブロッキング)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                input()  # 入力を消費
                break
            
            time.sleep(0.1)
        
        print(f"{motor_name}: 最小値 = {range_mins[motor_name]} 記録完了")
        
        # ステップ3: 最大値探索
        print(f"\n--- ステップ3: {motor_name} 最大値探索 ---")
        present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        range_maxes[motor_name] = present_pos
        
        while True:
            present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            range_maxes[motor_name] = max(range_maxes[motor_name], present_pos)
            
            # 画面をクリアして最大値探索状況を表示
            print("\033[2J\033[H", end="")  # 画面クリア
            print(f"SO101 フォロワー キャリブレーション - {motor_name} (ID: {motor_id})")
            print("=" * 50)
            print("ステップ3: 最大値探索")
            print(f"現在位置: {present_pos}")
            print(f"記録最大値: {range_maxes[motor_name]}")
            print(f"\n{motor_name} を最大位置まで動かし、完了したらENTERを押してください...")
            
            # ユーザー入力をチェック (ノンブロッキング)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                input()  # 入力を消費
                break
            
            time.sleep(0.1)
        
        print(f"{motor_name}: 最大値 = {range_maxes[motor_name]} 記録完了")
        
        # このモーターのキャリブレーション完了
        range_size = range_maxes[motor_name] - range_mins[motor_name]
        print(f"\n{motor_name} キャリブレーション完了:")
        print(f"  ホーミングオフセット: {homing_offsets[motor_name]}")
        print(f"  可動範囲: {range_mins[motor_name]} ～ {range_maxes[motor_name]} (幅: {range_size})")
        
        if motor_name != "gripper":  # 最後のモーター以外
            input(f"\nENTERを押して次のモーター ({list(SO101_MOTORS.keys())[list(SO101_MOTORS.values()).index(motor_id)+1]}) に進んでください...")
    
    print("\n=== 全モーターのキャリブレーション完了 ===")
    
    # 8. キャリブレーションを保存 (self._save_calibration()相当)
    print("\nキャリブレーション結果:")
    
    # 新しいキャリブレーションデータで設定を更新
    if 'follower' not in config:
        config['follower'] = {}
    if 'calibration' not in config['follower']:
        config['follower']['calibration'] = {}
    
    for motor_name, motor_id in SO101_MOTORS.items():
        config['follower']['calibration'][motor_name] = {
            'id': motor_id,
            'homing_offset': homing_offsets[motor_name],
            'range_min': range_mins[motor_name],
            'range_max': range_maxes[motor_name]
        }
        print(f"{motor_name}: オフセット={homing_offsets[motor_name]}, 最小={range_mins[motor_name]}, 最大={range_maxes[motor_name]}")
        
        # モーターに制限値を書き込み (self.bus.write_calibration()相当)
        packet_handler.write2ByteTxRx(port_handler, motor_id, 6, range_mins[motor_name])   # Min_Position_Limit
        packet_handler.write2ByteTxRx(port_handler, motor_id, 8, range_maxes[motor_name])  # Max_Position_Limit
    
    # 9. .env.yamlに保存
    save_config(config)
    calibration_file = f"~/.cache/huggingface/lerobot/calibration/robots/so101_follower/{robot_id}.json"
    print(f"キャリブレーションを .env.yaml に保存しました")
    print(f"(LeRobot相当: {calibration_file})")
    
    # 10. 切断
    port_handler.closePort()
    print("切断しました")

if __name__ == "__main__":
    main()
