#!/usr/bin/env python3
# モーターキャリブレーションスクリプト

import yaml
import time
import os
from scservo_sdk import *
from servo_constants import *

def get_current_position(portHandler, packetHandler, motor_id):
    """現在位置を取得"""
    position, _, _ = packetHandler.read2ByteTxRx(portHandler, motor_id, ADDR_PRESENT_POSITION)
    return position

def calibrate_all_motors(config, portHandler, packetHandler):
    """全モーターを一気にキャリブレーション"""
    # 表示順序を指定
    motor_order = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    motor_list = [(name, config['follower']['calibration'][name]) for name in motor_order]
    calibration_results = {}
    
    print("=== 全モーター一括キャリブレーション ===")
    print("各関節を手で動かして可動域を記録します")
    print()
    
    # 限界位置1を記録
    print("【ステップ1】各関節を一方の限界まで曲げてください")
    positions1 = wait_for_all_positions_input(motor_list, portHandler, packetHandler, "【ステップ1】各関節を一方の限界まで曲げてください")
    
    # 限界位置2を記録  
    print("【ステップ2】各関節を逆方向の限界まで曲げてください")
    positions2 = wait_for_all_positions_input(motor_list, portHandler, packetHandler, "【ステップ2】各関節を逆方向の限界まで曲げてください", positions1)
    
    # 中間位置を記録
    print("【ステップ3】各関節を物理的な中間位置（最も自然な位置）にしてください")
    print("この位置が論理的な中間位置(2048)として設定されます")
    middle_positions = wait_for_all_positions_input(motor_list, portHandler, packetHandler, "【ステップ3】各関節を物理的な中間位置にしてください", positions1, positions2)
    
    # 各モーターの結果を計算
    for motor_name, motor_data in motor_list:
        pos1 = positions1[motor_name]
        pos2 = positions2[motor_name]
        middle_actual = middle_positions[motor_name]
        
        range_min = min(pos1, pos2)
        range_max = max(pos1, pos2)
        
        # ホーミングオフセット計算（LeRobot方式）
        # 実際の中間位置を2048にするためのオフセット
        homing_offset = middle_actual - 2048
        
        # ホーミングオフセットをモーターに書き込み
        print(f"{motor_name}: ホーミングオフセット {homing_offset} を設定中...")
        packetHandler.write2ByteTxRx(portHandler, motor_data['id'], 20, homing_offset)  # Homing_Offset address = 20
        time.sleep(0.1)
        
        # 設定後の位置確認
        new_position, _, _ = packetHandler.read2ByteTxRx(portHandler, motor_data['id'], ADDR_PRESENT_POSITION)
        print(f"  設定後の位置: {new_position} (目標: 2048)")
        
        # 論理的な範囲を計算（ホーミングオフセット適用後）
        logical_min = range_min - homing_offset
        logical_max = range_max - homing_offset
        logical_middle = 2048  # 常に2048が中間
        
        # 単純な中間値
        simple_middle = (range_min + range_max) // 2
        
        # オーバーフロー中間値（4096を跨ぐ場合）
        overflow_middle = (range_max + (range_min + 4096)) // 2
        if overflow_middle >= 4096:
            overflow_middle -= 4096
        
        # 実際の中間位置により近い方を採用
        diff_simple = abs(middle_actual - simple_middle)
        diff_overflow = abs(middle_actual - overflow_middle)
        
        calculated_middle = overflow_middle if diff_overflow < diff_simple else simple_middle
        
        calibration_results[motor_name] = {
            "id": motor_data['id'],
            "range_min": logical_min,
            "range_max": logical_max,
            "middle": logical_middle,  # 常に2048
            "homing_offset": homing_offset,
            "physical_middle": middle_actual,
            "physical_min": range_min,
            "physical_max": range_max
        }
    
    # ホーミングオフセットは既に適用済み
    print("\n=== ホーミングオフセット適用済み ===")
    for motor_name, result in calibration_results.items():
        print(f"{motor_name}: オフセット = {result['homing_offset']} (適用済み)")
    
    print("\n現在の論理位置:")
    for motor_name, result in calibration_results.items():
        motor_id = result['id']
        current_pos, _, _ = packetHandler.read2ByteTxRx(portHandler, motor_id, ADDR_PRESENT_POSITION)
        print(f"{motor_name}: {current_pos} (目標: 2048)")
        
        print("ホーミングオフセット適用完了")
        print("注意: モーターの電源を一度切って入れ直してください")
    else:
        print("ホーミングオフセットはスキップしました")
    
    return calibration_results

def wait_for_all_positions_input(motor_list, portHandler, packetHandler, instruction="", pos1=None, pos2=None):
    """全モーターの位置をリアルタイム表示しながらENTER待ち"""
    import threading
    
    stop_display = False
    current_positions = {}
    
    def display_loop():
        nonlocal current_positions, stop_display
        while not stop_display:
            os.system('clear' if os.name == 'posix' else 'cls')
            if instruction:
                print(instruction)
                print()
            
            # 確定済みの値を表示
            if pos1:
                print("限界位置1:")
                for motor_name, _ in motor_list:
                    print(f"  {motor_name:12}: {pos1[motor_name]:4d}")
                print()
            
            if pos2:
                print("限界位置2:")
                for motor_name, _ in motor_list:
                    print(f"  {motor_name:12}: {pos2[motor_name]:4d}")
                print()
            
            print("現在位置:")
            for motor_name, motor_data in motor_list:
                pos = get_current_position(portHandler, packetHandler, motor_data['id'])
                current_positions[motor_name] = pos
                print(f"  {motor_name:12}: {pos:4d}")
            print("\nENTERで確定")
            time.sleep(0.05)
    
    # リアルタイム表示開始
    display_thread = threading.Thread(target=display_loop)
    display_thread.start()
    
    # ENTER待ち
    input()
    
    # 表示停止
    stop_display = True
    display_thread.join()
    print()  # 改行
    
    return current_positions.copy()
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
        print("モーターキャリブレーション開始")
        
        # キャリブレーション実行
        calibration_results = calibrate_all_motors(config, portHandler, packetHandler)
        
        # 結果を表示
        print("\n=== キャリブレーション結果 ===")
        for motor_name, result in calibration_results.items():
            print(f"{motor_name}: min={result['range_min']}, max={result['range_max']}, middle={result['middle']}")
        
        # .env.yamlにキャリブレーション結果を追記/上書き
        for motor_name, result in calibration_results.items():
            config['follower']['calibration'][motor_name].update({
                'range_min': result['range_min'],
                'range_max': result['range_max'],
                'middle': result['middle']
            })
        
        # .env.yamlに保存
        with open('.env.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print("\n結果を .env.yaml に保存しました")
        
    except KeyboardInterrupt:
        print("\n停止しました")
    finally:
        # 全モーターのトルクを無効化
        for motor_name, motor_data in config['follower']['calibration'].items():
            packetHandler.write1ByteTxRx(portHandler, motor_data['id'], ADDR_TORQUE_ENABLE, 0)
        portHandler.closePort()

if __name__ == "__main__":
    main()
