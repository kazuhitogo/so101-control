import yaml
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE, SO101_MOTORS, 
    ADDR_ID, COMM_SUCCESS
)


def setup_motors(port):
    """SO101 フォロワーアーム用のモーターIDを設定"""

    motors = SO101_MOTORS

    # PortHandlerとPacketHandlerを初期化
    portHandler = PortHandler(port)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    if not portHandler.openPort():
        print(f"ポート {port} を開けませんでした")
        return False

    portHandler.setBaudRate(BAUDRATE)

    for motor_name, target_id in reversed(list(motors.items())):
        input(
            f"'{motor_name}' モーターのみをコントローラーボードに接続してEnterを押してください。"
        )

        # 接続されたモーターをスキャン（通常はデフォルトでID 1）
        for scan_id in range(1, 10):
            dxl_model_number, dxl_comm_result, dxl_error = packetHandler.ping(
                portHandler, scan_id
            )
            if dxl_comm_result == COMM_SUCCESS:
                print(f"ID {scan_id} でモーターを発見、ID {target_id} に設定中")

                # IDを変更
                dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
                    portHandler, scan_id, ADDR_ID, target_id
                )

                if dxl_comm_result == COMM_SUCCESS:
                    print(f"'{motor_name}' モーターのIDを {target_id} に設定しました")
                else:
                    print(f"{motor_name} のID設定に失敗しました")
                break
        else:
            print(f"{motor_name} のモーターが見つかりませんでした")

    portHandler.closePort()
    return True


def main():
    try:
        with open(".env.yaml", "r") as f:
            config = yaml.safe_load(f)

        print("セットアップするアームを選択してください:")
        print("1. フォロワーアーム")
        print("2. リーダーアーム")
        choice = input("選択肢を入力してください (1 または 2): ")

        if choice == "1":
            port = config["follower"]["port"]
            print(f"フォロワーアーム ({port}) をセットアップ中")
        elif choice == "2":
            port = config["leader"]["port"]
            print(f"リーダーアーム ({port}) をセットアップ中")
        else:
            print("無効な選択です")
            return

        setup_motors(port)

    except FileNotFoundError:
        print(".env.yaml が見つかりません")
        return
    except KeyError:
        print(".env.yaml の設定形式が無効です")
        return


if __name__ == "__main__":
    main()
