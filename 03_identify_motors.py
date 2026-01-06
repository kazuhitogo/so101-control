import yaml
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE, ADDR_ID, COMM_SUCCESS
)


def identify_motors(port):
    """EEPROM から現在のモーター ID を読み取り"""

    portHandler = PortHandler(port)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    if not portHandler.openPort():
        print(f"ポート {port} を開けませんでした")
        return False

    portHandler.setBaudRate(BAUDRATE)

    print("モーターをスキャン中...")
    found_motors = []

    for motor_id in range(1, 10):
        current_id, dxl_comm_result, dxl_error = packetHandler.read1ByteTxRx(
            portHandler, motor_id, ADDR_ID
        )

        if dxl_comm_result == COMM_SUCCESS:
            print(f"ID {motor_id} でモーターを発見: 保存された ID = {current_id}")
            found_motors.append(motor_id)

    if not found_motors:
        print("モーターが見つかりませんでした")
    else:
        print(f"発見されたモーター数: {len(found_motors)}")

    portHandler.closePort()
    return True


def main():
    try:
        with open(".env.yaml", "r") as f:
            config = yaml.safe_load(f)

        print("=== フォロワーアーム ===")
        follower_port = config["follower"]["port"]
        print(f"ポート: {follower_port}")
        identify_motors(follower_port)

        print("\n=== リーダーアーム ===")
        leader_port = config["leader"]["port"]
        print(f"ポート: {leader_port}")
        identify_motors(leader_port)

    except FileNotFoundError:
        print(".env.yaml が見つかりません")
        return
    except KeyError:
        print(".env.yaml の設定形式が無効です")
        return


if __name__ == "__main__":
    main()
