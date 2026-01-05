import yaml
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE, SO101_MOTORS, 
    ADDR_ID, COMM_SUCCESS
)


def setup_motors(port):
    """Setup motor IDs for SO101 follower arm"""

    motors = SO101_MOTORS

    # Initialize PortHandler and PacketHandler
    portHandler = PortHandler(port)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    if not portHandler.openPort():
        print(f"Failed to open port {port}")
        return False

    portHandler.setBaudRate(BAUDRATE)

    for motor_name, target_id in reversed(list(motors.items())):
        input(
            f"Connect the controller board to the '{motor_name}' motor only and press enter."
        )

        # Scan for connected motor (usually ID 1 by default)
        for scan_id in range(1, 10):
            dxl_model_number, dxl_comm_result, dxl_error = packetHandler.ping(
                portHandler, scan_id
            )
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Found motor at ID {scan_id}, setting to ID {target_id}")

                # Change ID
                dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
                    portHandler, scan_id, ADDR_ID, target_id
                )

                if dxl_comm_result == COMM_SUCCESS:
                    print(f"'{motor_name}' motor id set to {target_id}")
                else:
                    print(f"Failed to set ID for {motor_name}")
                break
        else:
            print(f"No motor found for {motor_name}")

    portHandler.closePort()
    return True


def main():
    try:
        with open(".env.yaml", "r") as f:
            config = yaml.safe_load(f)

        print("Select arm to setup:")
        print("1. Follower arm")
        print("2. Leader arm")
        choice = input("Enter choice (1 or 2): ")

        if choice == "1":
            port = config["follower"]["port"]
            print(f"Setting up FOLLOWER arm on {port}")
        elif choice == "2":
            port = config["leader"]["port"]
            print(f"Setting up LEADER arm on {port}")
        else:
            print("Invalid choice")
            return

        setup_motors(port)

    except FileNotFoundError:
        print(".env.yaml not found")
        return
    except KeyError:
        print("Invalid config format in .env.yaml")
        return


if __name__ == "__main__":
    main()
