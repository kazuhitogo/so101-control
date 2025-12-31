import yaml
import time
import os
from scservo_sdk import *
from servo_constants import *

def get_current_position(portHandler, packetHandler, motor_id):
    """現在位置を取得"""
    position, _, _ = packetHandler.read2ByteTxRx(portHandler, motor_id, ADDR_PRESENT_POSITION)
    return position

def calibrate_motors_individually(config, portHandler, packetHandler):
    """モーターをID順に個別キャリブレーション"""
    motor_order = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    motor_list = [(name, config['follower']['calibration'][name]) for name in motor_order]
    calibration_results = {}
    
    # モーターIDでソート
    motor_list.sort(key=lambda x: x[1]['id'])
    
    for motor_name, motor_data in motor_list:
        motor_id = motor_data['id']
        print(f"\n=== モーター {motor_name} (ID: {motor_id}) のキャリブレーション ===")
        
        # 中間位置設定
        print(f"【ステップ1】{motor_name} を中間位置にしてください")
        middle_pos = wait_for_position_input(portHandler, packetHandler, motor_id, f"{motor_name} を中間位置にしてください")
        
        # ホーミングオフセット設定
        homing_offset = middle_pos - 2048
        
        # 負の値の場合、12bit unsigned intの2の補数表現に変換
        if homing_offset < 0:
            homing_offset = 4096 + homing_offset
        
        print(f"ホーミングオフセット {homing_offset} を設定中...")
        packetHandler.write2ByteTxRx(portHandler, motor_id, ADDR_HOMING_OFFSET, homing_offset)
        time.sleep(0.1)
        
        # 最小値設定
        print(f"【ステップ2】{motor_name} を最小位置にしてください")
        min_pos = wait_for_position_input(portHandler, packetHandler, motor_id, f"{motor_name} を最小位置にしてください")
        
        # 最大値設定
        print(f"【ステップ3】{motor_name} を最大位置にしてください")
        max_pos = wait_for_position_input(portHandler, packetHandler, motor_id, f"{motor_name} を最大位置にしてください")
        
        calibration_results[motor_name] = {
            "id": motor_id,
            "range_min": min_pos,
            "range_max": max_pos,
            "middle": 2048,
            "homing_offset": homing_offset
        }
        
        print(f"{motor_name} 完了: min={min_pos}, max={max_pos}, offset={homing_offset}")
    
    return calibration_results

def wait_for_position_input(portHandler, packetHandler, motor_id, instruction=""):
    """単一モーターの位置をリアルタイム表示しながらENTER待ち"""
    import threading
    
    stop_display = False
    current_position = 0
    
    def display_loop():
        nonlocal current_position, stop_display
        while not stop_display:
            os.system('clear' if os.name == 'posix' else 'cls')
            if instruction:
                print(instruction)
                print()
            
            pos = get_current_position(portHandler, packetHandler, motor_id)
            current_position = pos
            print(f"現在位置: {pos}")
            print("\nENTERで確定")
            time.sleep(0.05)
    
    display_thread = threading.Thread(target=display_loop)
    display_thread.start()
    
    input()
    
    stop_display = True
    display_thread.join()
    print()
    
    return current_position

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
        
        # 全モーターのトルクを無効化
        motor_order = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
        for motor_name in motor_order:
            motor_id = config['follower']['calibration'][motor_name]['id']
            packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
        
        # キャリブレーション実行
        calibration_results = calibrate_motors_individually(config, portHandler, packetHandler)
        
        # 結果を表示
        print("\n=== キャリブレーション結果 ===")
        for motor_name, result in calibration_results.items():
            print(f"{motor_name}: min={result['range_min']}, max={result['range_max']}, middle={result['middle']}")
            print(f"  ホーミングオフセット: {result['homing_offset']}")
        
        # .env.yamlにキャリブレーション結果を保存
        for motor_name, result in calibration_results.items():
            config['follower']['calibration'][motor_name].update({
                'range_min': result['range_min'],
                'range_max': result['range_max']
            })
        
        with open('.env.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print("\n結果を .env.yaml に保存しました")
        
    except KeyboardInterrupt:
        print("\n停止しました")
    finally:
        # 全モーターのトルクを無効化
        for motor_name in motor_order:
            motor_id = config['follower']['calibration'][motor_name]['id']
            packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
        portHandler.closePort()

if __name__ == "__main__":
    main()
