#!/usr/bin/env python3
# シンプルなロボットアーム制御GUI

import yaml
import tkinter as tk
from tkinter import ttk
import threading
import time
import signal
import sys
from scservo_sdk import *
from servo_constants import *

class SimpleRobotGUI:
    def __init__(self):
        # 設定ファイル読み込み
        with open('.env.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        # モーター順序
        self.motor_order = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
        
        # ポート接続
        self.portHandler = PortHandler(self.config['follower']['port'])
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)
        self.portHandler.openPort()
        self.portHandler.setBaudRate(BAUDRATE)
        
        # グリッパーのみトルク有効化
        gripper_id = self.config['follower']['calibration']['gripper']['id']
        self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, 33, 0)  # Position mode
        self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, ADDR_TORQUE_ENABLE, 1)
        
        # グリッパーの初期位置を取得
        self.gripper_base_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, gripper_id, ADDR_PRESENT_POSITION)
        self.current_gripper_pos = self.gripper_base_pos
        print(f"gripper current: {self.gripper_base_pos}")
        
        # GUI作成
        self.create_gui()
        
        # 更新スレッド開始
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Ctrl+C対応
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Simple Robot Control")
        self.root.geometry("400x400")
        
        # 位置表示ラベル
        self.position_labels = {}
        self.goal_labels = {}
        
        for motor_name in self.motor_order:
            frame = ttk.Frame(self.root)
            frame.pack(fill='x', padx=10, pady=5)
            
            # モーター名
            name_label = ttk.Label(frame, text=f"{motor_name}:", width=15)
            name_label.pack(side='left')
            
            # 現在位置表示
            pos_label = ttk.Label(frame, text="0000", width=6)
            pos_label.pack(side='left')
            self.position_labels[motor_name] = pos_label
            
            # 区切り
            ttk.Label(frame, text="/", width=2).pack(side='left')
            
            # 目標位置表示
            goal_label = ttk.Label(frame, text="0000", width=6)
            goal_label.pack(side='left')
            self.goal_labels[motor_name] = goal_label
        
        # グリッパー制御ボタン
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        ttk.Label(button_frame, text="Gripper Control:").pack()
        
        control_frame = ttk.Frame(button_frame)
        control_frame.pack(pady=10)
        
        # -10ボタン
        minus_button = ttk.Button(control_frame, text="-10", command=self.gripper_minus)
        minus_button.pack(side='left', padx=5)
        
        # +10ボタン
        plus_button = ttk.Button(control_frame, text="+10", command=self.gripper_plus)
        plus_button.pack(side='left', padx=5)
        
        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def gripper_plus(self):
        """グリッパー +10"""
        gripper_id = self.config['follower']['calibration']['gripper']['id']
        self.current_gripper_pos += 10
        self.packetHandler.write2ByteTxRx(self.portHandler, gripper_id, ADDR_GOAL_POSITION, self.current_gripper_pos)
        print(f"gripper moved to: {self.current_gripper_pos}")
    
    def gripper_minus(self):
        """グリッパー -10"""
        gripper_id = self.config['follower']['calibration']['gripper']['id']
        self.current_gripper_pos -= 10
        self.packetHandler.write2ByteTxRx(self.portHandler, gripper_id, ADDR_GOAL_POSITION, self.current_gripper_pos)
        print(f"gripper moved to: {self.current_gripper_pos}")
    
    def update_loop(self):
        """位置更新"""
        while self.running:
            try:
                # 全モーターの現在位置と目標位置を表示
                for motor_name in self.motor_order:
                    motor_id = self.config['follower']['calibration'][motor_name]['id']
                    
                    # 現在位置
                    position, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                    self.position_labels[motor_name].config(text=f"{position:4d}")
                    
                    # 目標位置
                    goal_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_GOAL_POSITION)
                    self.goal_labels[motor_name].config(text=f"{goal_pos:4d}")
                
                time.sleep(0.1)
            except:
                break
    
    def check_signals(self):
        """定期的にシグナルをチェック"""
        if self.running:
            self.root.after(100, self.check_signals)
    
    def signal_handler(self, signum, frame):
        """Ctrl+C時の処理"""
        print("\nCtrl+C detected. Stopping...")
        self.running = False
        self.stop_motors()
        self.root.quit()  # mainloopを終了
        sys.exit(0)
    
    def stop_motors(self):
        """モーターを安全に停止"""
        try:
            gripper_id = self.config['follower']['calibration']['gripper']['id']
            # 現在位置を取得
            current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, gripper_id, ADDR_PRESENT_POSITION)
            # 目標位置を現在位置に設定
            self.packetHandler.write2ByteTxRx(self.portHandler, gripper_id, ADDR_GOAL_POSITION, current_pos)
            # トルクを無効化
            self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, ADDR_TORQUE_ENABLE, 0)
            self.portHandler.closePort()
            print("Gripper stopped safely")
        except Exception as e:
            print(f"Error stopping motors: {e}")
    
    def signal_handler(self, signum, frame):
        """Ctrl+C時の処理"""
        print("\nCtrl+C detected. Stopping...")
        self.running = False
        self.stop_motors()
        sys.exit(0)
    
    def on_closing(self):
        """終了時の処理"""
        self.running = False
        self.stop_motors()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

def main():
    gui = None
    try:
        gui = SimpleRobotGUI()
        gui.run()
    except Exception as e:
        print(f"エラー: {e}")
        if gui:
            gui.stop_motors()

if __name__ == "__main__":
    main()
