#!/usr/bin/env python3

# Protocol constants
PROTOCOL_VERSION = 0  # Protocol end: 0 for STS/SMS servos

# Servo register addresses
# https://tech-blog.abeja.asia/entry/so101-motor-control-202508
ADDR_ID = 5
ADDR_HOMING_OFFSET = 31
ADDR_POSITION_P_GAIN = 21
ADDR_POSITION_D_GAIN = 22
ADDR_POSITION_I_GAIN = 23
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_LOCK = 55
ADDR_PRESENT_POSITION = 56

# Communication settings
BAUDRATE = 1000000

# Motor configurations
SO101_MOTORS = {
    "shoulder_pan": 1,
    "shoulder_lift": 2,
    "elbow_flex": 3,
    "wrist_flex": 4,
    "wrist_roll": 5,
    "gripper": 6,
}
