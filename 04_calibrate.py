#!/usr/bin/env python3

import time
import yaml
import select
import sys
import scservo_sdk as scs
from servo_constants import *

def load_config():
    """Load configuration from .env.yaml"""
    with open('.env.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config

def save_config(config):
    """Save configuration to .env.yaml"""
    with open('.env.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)

def main():
    print("SO101 Follower Calibration")
    print("=" * 40)
    
    # 1. Load configuration from .env.yaml
    config = load_config()
    port = config['follower']['port']
    robot_id = "my_first_follower_arm"  # From .env.yaml structure
    
    # 2. Initialize FeetechMotorsBus equivalent
    port_handler = scs.PortHandler(port)
    packet_handler = scs.PacketHandler(PROTOCOL_VERSION)
    
    # 3. Connect to port
    if not port_handler.openPort():
        print(f"Failed to open port {port}")
        return
    
    if not port_handler.setBaudRate(BAUDRATE):
        print(f"Failed to set baudrate {BAUDRATE}")
        return
    
    print(f"Connected to {port}")
    
    # 4. Check if calibration exists (equivalent to SO101Follower.calibrate())
    existing_calibration = config.get('follower', {}).get('calibration', {})
    
    if existing_calibration:
        user_input = input(
            f"Press ENTER to use provided calibration file associated with the id {robot_id}, "
            f"or type 'c' and press ENTER to run calibration: "
        )
        if user_input.strip().lower() != "c":
            print(f"Writing calibration file associated with the id {robot_id} to the motors")
            # Write existing calibration to motors
            for motor_name, motor_id in SO101_MOTORS.items():
                if motor_name in existing_calibration:
                    cal = existing_calibration[motor_name]
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 31, cal['homing_offset'])  # Homing_Offset
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 6, cal['range_min'])       # Min_Position_Limit
                    packet_handler.write2ByteTxRx(port_handler, motor_id, 8, cal['range_max'])       # Max_Position_Limit
            print("Calibration written to motors")
            port_handler.closePort()
            return
    
    print(f"\nRunning calibration of SO101 Follower")
    
    # 5. Disable torque (equivalent to self.bus.disable_torque())
    for motor_name, motor_id in SO101_MOTORS.items():
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)  # Torque_Enable = 0
        packet_handler.write1ByteTxRx(port_handler, motor_id, 55, 0)                  # Lock = 0
    
    # 6. Set operating mode to position (equivalent to OperatingMode.POSITION.value)
    for motor_name, motor_id in SO101_MOTORS.items():
        packet_handler.write1ByteTxRx(port_handler, motor_id, 33, 0)  # Operating_Mode = 0 (POSITION)
    
    # 7. Set middle position (equivalent to self.bus.set_half_turn_homings())
    input(f"Move SO101 Follower to the middle of its range of motion and press ENTER....")
    
    homing_offsets = {}
    for motor_name, motor_id in SO101_MOTORS.items():
        # Read present position
        present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        # Calculate homing offset (center = 2047 for 12-bit encoder)
        homing_offset = present_pos - 2047
        homing_offsets[motor_name] = homing_offset
        # Write homing offset
        packet_handler.write2ByteTxRx(port_handler, motor_id, 31, homing_offset)  # Homing_Offset
        print(f"{motor_name}: homing_offset = {homing_offset}")
    
    # 8. Record range of motion (equivalent to self.bus.record_ranges_of_motion())
    print(
        "Move all joints sequentially through their entire ranges "
        "of motion.\nRecording positions. Press ENTER to stop..."
    )
    
    # Initialize with current positions
    range_mins = {}
    range_maxes = {}
    for motor_name, motor_id in SO101_MOTORS.items():
        present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        range_mins[motor_name] = present_pos
        range_maxes[motor_name] = present_pos
    
    # Record ranges with real-time display
    while True:
        # Read all positions
        positions = {}
        for motor_name, motor_id in SO101_MOTORS.items():
            present_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            positions[motor_name] = present_pos
            range_mins[motor_name] = min(range_mins[motor_name], present_pos)
            range_maxes[motor_name] = max(range_maxes[motor_name], present_pos)
        
        # Clear screen and show positions with ranges
        print("\033[2J\033[H", end="")  # Clear screen
        print("SO101 Follower Calibration - Range Recording")
        print("=" * 60)
        print(f"{'Motor':15} {'Current':>7} {'Min':>7} {'Max':>7} {'Range':>7}")
        print("-" * 60)
        for motor_name in SO101_MOTORS.keys():
            current = positions[motor_name]
            min_pos = range_mins[motor_name]
            max_pos = range_maxes[motor_name]
            range_size = max_pos - min_pos
            print(f"{motor_name:15} {current:7d} {min_pos:7d} {max_pos:7d} {range_size:7d}")
        print("\nMove all joints through full range and press ENTER when done...")
        
        # Check for user input (non-blocking)
        if select.select([sys.stdin], [], [], 0.1)[0]:
            input()  # consume the input
            break
        
        time.sleep(0.1)
    
    # 9. Save calibration (equivalent to self._save_calibration())
    print("\nCalibration results:")
    
    # Update config with new calibration data
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
        print(f"{motor_name}: offset={homing_offsets[motor_name]}, min={range_mins[motor_name]}, max={range_maxes[motor_name]}")
        
        # Write limits to motors (equivalent to self.bus.write_calibration())
        packet_handler.write2ByteTxRx(port_handler, motor_id, 6, range_mins[motor_name])   # Min_Position_Limit
        packet_handler.write2ByteTxRx(port_handler, motor_id, 8, range_maxes[motor_name])  # Max_Position_Limit
    
    # 10. Save to .env.yaml
    save_config(config)
    calibration_file = f"~/.cache/huggingface/lerobot/calibration/robots/so101_follower/{robot_id}.json"
    print(f"Calibration saved to .env.yaml")
    print(f"(LeRobot equivalent: {calibration_file})")
    
    # 11. Disconnect
    port_handler.closePort()
    print("Disconnected")

if __name__ == "__main__":
    main()
