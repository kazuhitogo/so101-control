import yaml
import scservo_sdk as scs
from servo_constants import *
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
        # トルクの無効化
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)
        # EPROM 書き込みロック解除
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_LOCK, 0)


    motor_id = config['follower']['calibration']['shoulder_pan']['id']
    
    try:
        # オフセットを 0 で初期化
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_HOMING_OFFSET, 0)
        port_reconnect()
        now_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        print(f"現在のオフセット: 0, 現在の位置: {now_pos}")
        # オフセットを + 10する
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_HOMING_OFFSET, 10)
        port_reconnect()
        plus_10_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        print(f"plus 10 のオフセット: 10, plus 10 の位置: {plus_10_pos}")

        # 差が 4000 を超えていたらオーバーフロー
        if abs(now_pos - plus_10_pos) > 4000:
            now_pos = now_pos + 4096 if now_pos < plus_10_pos else now_pos
            plus_10_pos = plus_10_pos + 4096 if now_pos > plus_10_pos else plus_10_pos
        
        if now_pos > plus_10_pos: # オフセットを増やせば位置座標が減る場合
            optimized_offset = now_pos - 2047
        else: # オフセットを増やせば位置座標が増える場合
            optimized_offset = 2047 - now_pos
        optimized_offset = optimized_offset if optimized_offset >= 0 else optimized_offset + 4096
        
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_HOMING_OFFSET, optimized_offset)
        port_reconnect()

        optimized_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        print(f"最適化されたオフセット: {optimized_offset}, 最適化された位置: {optimized_pos}")
        sleep(1)
        min_pos = 4095
        max_pos = 0
        while True:
            pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            min_pos = min_pos if pos > min_pos else pos
            max_pos = max_pos if pos < max_pos else pos
            print("\033[2J\033[H", end="") 
            print( f"オフセット: {optimized_offset}")
            print( f"現在値: {pos}")
            print( f"最小値: {min_pos}")
            print( f"最大値: {max_pos}")
            if select.select([sys.stdin], [], [], 0.1)[0]:
                input()  # 入力を消費
                break

        

        



    except Exception as e:
        print(f"エラー: {e}")
    finally:
        port_handler.closePort()        

if __name__ == "__main__":
    main()
