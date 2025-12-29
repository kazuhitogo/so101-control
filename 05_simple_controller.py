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
        
        # グリッパーのトルク状態を管理
        gripper_id = self.config['follower']['calibration']['gripper']['id']
        self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, 33, 0)  # Position mode
        
        # 現在のトルク状態を取得
        torque_status, _, _ = self.packetHandler.read1ByteTxRx(self.portHandler, gripper_id, ADDR_TORQUE_ENABLE)
        self.gripper_torque_enabled = bool(torque_status)
        
        # グリッパーの初期位置を取得
        self.gripper_base_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, gripper_id, ADDR_PRESENT_POSITION)
        self.current_gripper_pos = self.gripper_base_pos
        
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
        self.root.title("Robot Control with Sliders")
        self.root.geometry("700x450")
        
        # 位置表示ラベルとスライダー
        self.position_labels = {}
        self.sliders = {}
        self.goal_labels = {}  # 辞書として初期化
        
        for motor_name in self.motor_order:
            frame = ttk.Frame(self.root)
            frame.pack(fill='x', padx=10, pady=5)
            
            # スライダー（グリッパーのみ有効）
            if motor_name == 'gripper':
                motor_config = self.config['follower']['calibration'][motor_name]
                range_min = motor_config.get('range_min', 0)
                range_max = motor_config.get('range_max', 4095)
                
                # スライダー行
                slider_frame = ttk.Frame(frame)
                slider_frame.pack(fill='x')
                
                ttk.Label(slider_frame, text=f"{motor_name}:", width=15).pack(side='left')
                
                # 左端：Target値
                goal_label = ttk.Label(slider_frame, text=f"{int(self.current_gripper_pos):4d}", width=6, foreground='orange', font=('TkDefaultFont', 10, 'bold'))
                goal_label.pack(side='left')
                self.goal_labels[motor_name] = goal_label
                
                slider = ttk.Scale(
                    slider_frame,
                    from_=range_min,
                    to=range_max,
                    orient='horizontal',
                    length=300
                )
                slider.set(self.current_gripper_pos)
                slider.pack(side='left', fill='x', expand=True, padx=5)
                self.sliders[motor_name] = slider
                
                # 右端：Current値
                pos_label = ttk.Label(slider_frame, text=f"{int(self.current_gripper_pos):4d}", width=6, foreground='red', font=('TkDefaultFont', 10, 'bold'))
                pos_label.pack(side='left')
                self.position_labels[motor_name] = pos_label
                
                # 範囲表示
                range_label = ttk.Label(slider_frame, text=f"({range_min}-{range_max})", width=15)
                range_label.pack(side='left', padx=(10, 0))
                
                # トルクON/OFFボタン
                torque_frame = ttk.Frame(frame)
                torque_frame.pack(fill='x', pady=5)
                
                ttk.Label(torque_frame, text="", width=15).pack(side='left')  # 空白
                
                # トルクボタンの初期表示を現在状態に合わせる
                if self.gripper_torque_enabled:
                    button_text = "Torque ON"
                    status_text = "(Active)"
                    status_color = 'orange'
                else:
                    button_text = "Torque OFF"
                    status_text = "(Safe Mode)"
                    status_color = 'green'
                
                self.torque_button = ttk.Button(torque_frame, text=button_text, command=self.toggle_torque, width=12)
                self.torque_button.pack(side='left')
                
                self.torque_status_label = ttk.Label(torque_frame, text=status_text, foreground=status_color, font=('TkDefaultFont', 9))
                self.torque_status_label.pack(side='left', padx=(10, 0))
                
                # スライダーのcommandを設定
                slider.config(command=lambda val, name=motor_name: self.on_slider_change(name, val))
                
            else:
                # 他のモーターはシンプル表示
                simple_frame = ttk.Frame(frame)
                simple_frame.pack(fill='x')
                
                name_label = ttk.Label(simple_frame, text=f"{motor_name}:", width=15)
                name_label.pack(side='left')
                
                pos_label = ttk.Label(simple_frame, text="0000", width=6)
                pos_label.pack(side='left')
                self.position_labels[motor_name] = pos_label
        
        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_torque(self):
        """トルクのON/OFF切り替え"""
        gripper_id = self.config['follower']['calibration']['gripper']['id']
        
        if self.gripper_torque_enabled:
            # トルクOFF
            # 現在位置を目標位置に設定してから無効化
            current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, gripper_id, ADDR_PRESENT_POSITION)
            self.packetHandler.write2ByteTxRx(self.portHandler, gripper_id, ADDR_GOAL_POSITION, current_pos)
            self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, ADDR_TORQUE_ENABLE, 0)
            
            self.gripper_torque_enabled = False
            self.torque_button.config(text="Torque OFF")
            self.torque_status_label.config(text="(Safe Mode)", foreground='green')
            # スライダーは有効のまま（Target値設定用）
        else:
            # トルクON
            self.packetHandler.write1ByteTxRx(self.portHandler, gripper_id, ADDR_TORQUE_ENABLE, 1)
            
            self.gripper_torque_enabled = True
            self.torque_button.config(text="Torque ON")
            self.torque_status_label.config(text="(Active)", foreground='orange')
            self.sliders['gripper'].config(state='normal')
    
    def on_slider_change(self, motor_name, value):
        """スライダー変更時の処理"""
        position = int(float(value))
        print(f"Slider changed: {motor_name} = {position}")  # デバッグ用
        
        # 目標値表示を常に更新（キーが存在する場合のみ）
        if motor_name in self.goal_labels:
            self.goal_labels[motor_name].config(text=f"{position:4d}")
        else:
            print(f"Warning: goal_labels['{motor_name}'] not found")  # デバッグ用
        
        # トルクが有効な場合のみモーターに送信
        if self.gripper_torque_enabled:
            motor_id = self.config['follower']['calibration'][motor_name]['id']
            self.packetHandler.write2ByteTxRx(self.portHandler, motor_id, ADDR_GOAL_POSITION, position)
            print(f"Motor command sent: {position}")  # デバッグ用
    
    def update_loop(self):
        """位置更新"""
        while self.running:
            try:
                # 全モーターの現在位置を表示
                for motor_name in self.motor_order:
                    motor_id = self.config['follower']['calibration'][motor_name]['id']
                    position, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                    
                    if motor_name == 'gripper':
                        self.position_labels[motor_name].config(text=f"{position:4d}")
                        
                        # トルク状態も定期的に確認
                        torque_status, _, _ = self.packetHandler.read1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE)
                        actual_torque_enabled = bool(torque_status)
                        
                        # 状態が変わった場合は表示を更新
                        if actual_torque_enabled != self.gripper_torque_enabled:
                            self.gripper_torque_enabled = actual_torque_enabled
                            if self.gripper_torque_enabled:
                                self.torque_button.config(text="Torque ON")
                                self.torque_status_label.config(text="(Active)", foreground='orange')
                            else:
                                self.torque_button.config(text="Torque OFF")
                                self.torque_status_label.config(text="(Safe Mode)", foreground='green')
                    else:
                        self.position_labels[motor_name].config(text=f"{position:4d}")
                
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
