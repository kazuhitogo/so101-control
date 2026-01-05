import yaml
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE, ADDR_ID, COMM_SUCCESS
)


def identify_motors(port):
    """Read current motor IDs from EEPROM"""

    portHandler = PortHandler(port)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    if not portHandler.openPort():
        print(f"Failed to open port {port}")
        return False

    portHandler.setBaudRate(BAUDRATE)

    print("Scanning for motors...")
    found_motors = []

    for motor_id in range(1, 10):
        current_id, dxl_comm_result, dxl_error = packetHandler.read1ByteTxRx(
            portHandler, motor_id, ADDR_ID
        )

        if dxl_comm_result == COMM_SUCCESS:
            print(f"Motor found at ID {motor_id}: stored ID = {current_id}")
            found_motors.append(motor_id)

    if not found_motors:
        print("No motors found")
    else:
        print(f"Total motors found: {len(found_motors)}")

    portHandler.closePort()
    return True


def main():
    try:
        with open(".env.yaml", "r") as f:
            config = yaml.safe_load(f)

        print("=== FOLLOWER ARM ===")
        follower_port = config["follower"]["port"]
        print(f"Port: {follower_port}")
        identify_motors(follower_port)

        print("\n=== LEADER ARM ===")
        leader_port = config["leader"]["port"]
        print(f"Port: {leader_port}")
        identify_motors(leader_port)

    except FileNotFoundError:
        print(".env.yaml not found")
        return
    except KeyError:
        print("Invalid config format in .env.yaml")
        return


if __name__ == "__main__":
    main()
