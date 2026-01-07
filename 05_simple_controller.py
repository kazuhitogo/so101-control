#!/usr/bin/env python3
# シンプルなロボットアーム制御GUI

import yaml
import tkinter as tk
from tkinter import ttk
import threading
import time
import signal
import sys
from scservo_sdk import PortHandler, PacketHandler
from servo_constants import (
    PROTOCOL_VERSION, BAUDRATE,
    ADDR_TORQUE_ENABLE, ADDR_PRESENT_POSITION, ADDR_GOAL_POSITION,
    ADDR_POSITION_P_GAIN, ADDR_POSITION_I_GAIN, ADDR_POSITION_D_GAIN, 
)

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
        
        # 全モーターのトルク状態を管理
        self.motor_torque_enabled = {}
        
        for motor_name in self.motor_order:
            motor_id = self.config['follower']['calibration'][motor_name]['id']
            self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, 33, 0)  # Position mode
            
            # PID制御パラメータ設定
            self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_POSITION_P_GAIN, 16)  # P_Coefficient
            self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_POSITION_I_GAIN, 0)   # I_Coefficient  
            self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_POSITION_D_GAIN, 32)  # D_Coefficient
            
            # 現在のトルク状態を取得
            torque_status, _, _ = self.packetHandler.read1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE)
            self.motor_torque_enabled[motor_name] = bool(torque_status)
        
        # グリッパーの初期位置を取得
        gripper_id = self.config['follower']['calibration']['gripper']['id']
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
        self.goal_labels = {}
        
        for motor_name in self.motor_order:
            frame = ttk.Frame(self.root)
            frame.pack(fill='x', padx=10, pady=5)
            
            motor_config = self.config['follower']['calibration'][motor_name]
            range_min = motor_config.get('range_min', 0)
            range_max = motor_config.get('range_max', 4095)
            
            # 現在位置を取得
            motor_id = motor_config['id']
            current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
            
            # スライダー行
            slider_frame = ttk.Frame(frame)
            slider_frame.pack(fill='x')
            
            ttk.Label(slider_frame, text=f"{motor_name}:", width=15).pack(side='left')
            
            # 左端：Target値
            goal_label = ttk.Label(slider_frame, text=f"{current_pos:4d}", width=6, foreground='orange', font=('TkDefaultFont', 10, 'bold'))
            goal_label.pack(side='left')
            self.goal_labels[motor_name] = goal_label
            
            slider = ttk.Scale(
                slider_frame,
                from_=range_min,
                to=range_max,
                orient='horizontal',
                length=300
            )
            slider.set(current_pos)
            slider.pack(side='left', fill='x', expand=True, padx=5)
            self.sliders[motor_name] = slider
            
            # 右端：Current値
            pos_label = ttk.Label(slider_frame, text=f"{current_pos:4d}", width=6, foreground='red', font=('TkDefaultFont', 10, 'bold'))
            pos_label.pack(side='left')
            self.position_labels[motor_name] = pos_label
            
            # 範囲表示
            range_label = ttk.Label(slider_frame, text=f"({range_min}-{range_max})", width=15)
            range_label.pack(side='left', padx=(10, 0))
            
            # スライダーのcommandを設定
            slider.config(command=lambda val, name=motor_name: self.on_slider_change(name, val))
        
        # 一括トルクON/OFFボタン
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=20)
        
        # 全モーターのトルク状態を確認
        all_torque_enabled = all(self.motor_torque_enabled.values())
        
        if all_torque_enabled:
            button_text = "All Torque ON"
            status_text = "(All Active)"
            status_color = 'orange'
        else:
            button_text = "All Torque OFF"
            status_text = "(All Safe Mode)"
            status_color = 'green'
        
        self.all_torque_button = ttk.Button(control_frame, text=button_text, command=self.toggle_all_torque, width=15)
        self.all_torque_button.pack(side='left')
        
        self.all_torque_status_label = ttk.Label(control_frame, text=status_text, foreground=status_color, font=('TkDefaultFont', 10, 'bold'))
        self.all_torque_status_label.pack(side='left', padx=(10, 0))
        
        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_all_torque(self):
        """全モーターのトルクを一括ON/OFF切り替え"""
        all_torque_enabled = all(self.motor_torque_enabled.values())
        
        if all_torque_enabled:
            # 全モーターのトルクOFF
            for motor_name in self.motor_order:
                motor_id = self.config['follower']['calibration'][motor_name]['id']
                # 現在位置を目標位置に設定してから無効化
                current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                self.packetHandler.write2ByteTxRx(self.portHandler, motor_id, ADDR_GOAL_POSITION, current_pos)
                self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
                self.motor_torque_enabled[motor_name] = False
                
                # Target値とスライダーを現在位置に設定
                self.goal_labels[motor_name].config(text=f"{current_pos:4d}")
                self.sliders[motor_name].set(current_pos)
            
            self.all_torque_button.config(text="All Torque OFF")
            self.all_torque_status_label.config(text="(All Safe Mode)", foreground='green')
        else:
            # 全モーターのトルクON
            for motor_name in self.motor_order:
                motor_id = self.config['follower']['calibration'][motor_name]['id']
                # 現在位置を取得してTarget値とスライダーに設定
                current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                self.goal_labels[motor_name].config(text=f"{current_pos:4d}")
                self.sliders[motor_name].set(current_pos)
                
                # トルクON
                self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE, 1)
                self.motor_torque_enabled[motor_name] = True
            
            self.all_torque_button.config(text="All Torque ON")
            self.all_torque_status_label.config(text="(All Active)", foreground='orange')
    
    def on_slider_change(self, motor_name, value):
        """スライダー変更時の処理"""
        position = int(float(value))
        print(f"スライダー変更: {motor_name} = {position}")  # デバッグ用
        
        # 目標値表示を常に更新（キーが存在する場合のみ）
        if motor_name in self.goal_labels:
            self.goal_labels[motor_name].config(text=f"{position:4d}")
        else:
            print(f"警告: goal_labels['{motor_name}'] が見つかりません")  # デバッグ用
        
        # トルクが有効な場合のみモーターに送信
        if self.motor_torque_enabled.get(motor_name, False):
            motor_id = self.config['follower']['calibration'][motor_name]['id']
            self.packetHandler.write2ByteTxRx(self.portHandler, motor_id, ADDR_GOAL_POSITION, position)
            print(f"モーターコマンド送信: {position}")  # デバッグ用
    
    def update_loop(self):
        """位置更新"""
        while self.running:
            try:
                # 全モーターの現在位置を表示
                for motor_name in self.motor_order:
                    motor_id = self.config['follower']['calibration'][motor_name]['id']
                    position, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                    self.position_labels[motor_name].config(text=f"{position:4d}")
                    
                    # トルク状態も定期的に確認
                    torque_status, _, _ = self.packetHandler.read1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE)
                    self.motor_torque_enabled[motor_name] = bool(torque_status)
                
                # 一括トルクボタンの表示を更新
                all_torque_enabled = all(self.motor_torque_enabled.values())
                if all_torque_enabled:
                    self.all_torque_button.config(text="All Torque ON")
                    self.all_torque_status_label.config(text="(All Active)", foreground='orange')
                else:
                    self.all_torque_button.config(text="All Torque OFF")
                    self.all_torque_status_label.config(text="(All Safe Mode)", foreground='green')
                
                time.sleep(0.1)
            except Exception:
                break
    
    def check_signals(self):
        """定期的にシグナルをチェック"""
        if self.running:
            self.root.after(100, self.check_signals)
    
    def signal_handler(self, signum, frame):
        """Ctrl+C時の処理"""
        print("\nCtrl+C が検出されました。停止中...")
        self.running = False
        self.stop_motors()
        self.root.quit()  # mainloopを終了
        sys.exit(0)
    
    def stop_motors(self):
        """モーターを安全に停止"""
        try:
            for motor_name in self.motor_order:
                motor_id = self.config['follower']['calibration'][motor_name]['id']
                # 現在位置を取得
                current_pos, _, _ = self.packetHandler.read2ByteTxRx(self.portHandler, motor_id, ADDR_PRESENT_POSITION)
                # 目標位置を現在位置に設定
                self.packetHandler.write2ByteTxRx(self.portHandler, motor_id, ADDR_GOAL_POSITION, current_pos)
                # トルクを無効化
                self.packetHandler.write1ByteTxRx(self.portHandler, motor_id, ADDR_TORQUE_ENABLE, 0)
            self.portHandler.closePort()
        except Exception as e:
            print(f"モーター停止エラー: {e}")
    
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
