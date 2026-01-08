import yaml
import scservo_sdk as scs
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE, SO101_MOTORS,
    ADDR_TORQUE_ENABLE, ADDR_LOCK, ADDR_HOMING_OFFSET, ADDR_PRESENT_POSITION
)
from time import sleep
import select
import sys

with open('.env.yaml', 'r') as f:
    config = yaml.safe_load(f)

port_handler = scs.PortHandler(config['follower']['port'])
packet_handler = scs.PacketHandler(PROTOCOL_VERSION)

def port_reconnect():
    sleep(0.1)
    port_handler.closePort()
    port_handler.openPort()
    port_handler.setBaudRate(BAUDRATE)
    return None


def main():
    port_handler.openPort()
    port_handler.setBaudRate(BAUDRATE)

    
    for motor_name, motor_id in SO101_MOTORS.items():
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_LOCK, 0)

    try:
        for motor_name in SO101_MOTORS.keys():
            motor_id = config['follower']['calibration'][motor_name]['id']
            print(f"\n=== {motor_name} (ID: {motor_id}) のキャリブレーション ===")
            print(f"{motor_name} を中間位置にセットしたら Enter を押してください")
            while input() != "":
                print("Enterキーを押してください")
                continue
            packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_HOMING_OFFSET, 0)
            port_reconnect()
            now_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            optimized_offset = now_pos - 2047
            packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_HOMING_OFFSET, optimized_offset)
            port_reconnect()

            min_pos = 4095
            max_pos = 0
            while True:
                pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
                min_pos = min_pos if pos > min_pos else pos
                max_pos = max_pos if pos < max_pos else pos
                print("\033[2J\033[H", end="") 
                print(f"=== {motor_name} を限界まで動かして最小と最大値を定義します ===")
                print( f"オフセット: {optimized_offset}")
                print( f"現在値: {pos}")
                print( f"最小値: {min_pos}")
                print( f"最大値: {max_pos}")
                print("Enterキーで次のモーターへ")
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = input()
                    if user_input == "":
                        break
            
            config['follower']['calibration'][motor_name]['homing_offset'] = optimized_offset
            config['follower']['calibration'][motor_name]['range_min'] = min_pos
            config['follower']['calibration'][motor_name]['range_max'] = max_pos
            
            print(f"{motor_name} のキャリブレーション完了")
        
        with open('.env.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print("\n全モーターのキャリブレーション完了 - .env.yamlに保存しました")

    except Exception as e:
        print(f"エラー: {e}")
    finally:
        port_handler.closePort()        

if __name__ == "__main__":
    main()
