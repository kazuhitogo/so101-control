#!/usr/bin/env python3
# LeaderとFollowerを同時に操作するGUI

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
    ADDR_OPERATING_MODE,
)

class DualRobotGUI:
    def __init__(self):
        # 設定ファイル読み込み
        with open('.env.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        # モーター順序
        self.motor_order = sorted(
            self.config['follower']['calibration'].keys(),
            key=lambda motor_name: self.config['follower']['calibration'][motor_name]['id']
        )
        
        # 両方のポート接続
        self.ports = {}
        self.packet_handlers = {}
        self.motor_torque_enabled = {}
        
        for arm_type in ['follower', 'leader']:
            port_handler = PortHandler(self.config[arm_type]['port'])
            port_handler.openPort()
            port_handler.setBaudRate(BAUDRATE)
            self.ports[arm_type] = port_handler
            self.packet_handlers[arm_type] = PacketHandler(PROTOCOL_VERSION)
            self.motor_torque_enabled[arm_type] = {}
            
            # 各モーターの初期化
            for motor_name in self.motor_order:
                motor_id = self.config[arm_type]['calibration'][motor_name]['id']
                packet_handler = self.packet_handlers[arm_type]
                
                packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_OPERATING_MODE, 0)
                packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_POSITION_P_GAIN, 16)
                packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_POSITION_I_GAIN, 0)
                packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_POSITION_D_GAIN, 32)
                
                torque_status, _, _ = packet_handler.read1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE)
                self.motor_torque_enabled[arm_type][motor_name] = bool(torque_status)
        
        # GUI作成
        self.create_gui()
        
        # 更新スレッド開始
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Dual Robot Control - Leader & Follower")
        self.root.geometry("1400x500")
        
        # メインフレーム（左右分割）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.position_labels = {}
        self.sliders = {}
        self.goal_labels = {}
        self.torque_buttons = {}
        self.torque_status_labels = {}
        
        # Follower（左）とLeader（右）
        for idx, arm_type in enumerate(['follower', 'leader']):
            arm_frame = ttk.LabelFrame(main_frame, text=arm_type.upper(), padding=10)
            arm_frame.grid(row=0, column=idx, sticky='nsew', padx=5)
            
            self.position_labels[arm_type] = {}
            self.sliders[arm_type] = {}
            self.goal_labels[arm_type] = {}
            
            for motor_name in self.motor_order:
                frame = ttk.Frame(arm_frame)
                frame.pack(fill='x', pady=5)
                
                motor_config = self.config[arm_type]['calibration'][motor_name]
                range_min = motor_config.get('range_min', 0)
                range_max = motor_config.get('range_max', 4095)
                motor_id = motor_config['id']
                
                current_pos, _, _ = self.packet_handlers[arm_type].read2ByteTxRx(
                    self.ports[arm_type], motor_id, ADDR_PRESENT_POSITION
                )
                
                slider_frame = ttk.Frame(frame)
                slider_frame.pack(fill='x')
                
                ttk.Label(slider_frame, text=f"{motor_name}:", width=15).pack(side='left')
                
                goal_label = ttk.Label(slider_frame, text=f"{current_pos:4d}", width=6, 
                                      foreground='orange', font=('TkDefaultFont', 10, 'bold'))
                goal_label.pack(side='left')
                self.goal_labels[arm_type][motor_name] = goal_label
                
                slider = ttk.Scale(slider_frame, from_=range_min, to=range_max, 
                                  orient='horizontal', length=250)
                slider.set(current_pos)
                slider.pack(side='left', fill='x', expand=True, padx=5)
                self.sliders[arm_type][motor_name] = slider
                
                pos_label = ttk.Label(slider_frame, text=f"{current_pos:4d}", width=6, 
                                     foreground='red', font=('TkDefaultFont', 10, 'bold'))
                pos_label.pack(side='left')
                self.position_labels[arm_type][motor_name] = pos_label
                
                range_label = ttk.Label(slider_frame, text=f"({range_min}-{range_max})", width=15)
                range_label.pack(side='left', padx=(10, 0))
                
                slider.config(command=lambda val, a=arm_type, n=motor_name: self.on_slider_change(a, n, val))
            
            # トルクボタン
            control_frame = ttk.Frame(arm_frame)
            control_frame.pack(pady=15)
            
            all_torque_enabled = all(self.motor_torque_enabled[arm_type].values())
            button_text = "All Torque ON" if all_torque_enabled else "All Torque OFF"
            status_text = "(Active)" if all_torque_enabled else "(Safe Mode)"
            status_color = 'orange' if all_torque_enabled else 'green'
            
            torque_button = ttk.Button(control_frame, text=button_text, 
                                      command=lambda a=arm_type: self.toggle_all_torque(a), width=15)
            torque_button.pack(side='left')
            self.torque_buttons[arm_type] = torque_button
            
            status_label = ttk.Label(control_frame, text=status_text, foreground=status_color, 
                                    font=('TkDefaultFont', 10, 'bold'))
            status_label.pack(side='left', padx=(10, 0))
            self.torque_status_labels[arm_type] = status_label
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_all_torque(self, arm_type):
        """指定アームの全モーターのトルクを一括ON/OFF"""
        all_torque_enabled = all(self.motor_torque_enabled[arm_type].values())
        
        for motor_name in self.motor_order:
            motor_id = self.config[arm_type]['calibration'][motor_name]['id']
            current_pos, _, _ = self.packet_handlers[arm_type].read2ByteTxRx(
                self.ports[arm_type], motor_id, ADDR_PRESENT_POSITION
            )
            
            if all_torque_enabled:
                # トルクOFF
                self.packet_handlers[arm_type].write2ByteTxRx(
                    self.ports[arm_type], motor_id, ADDR_GOAL_POSITION, current_pos
                )
                self.packet_handlers[arm_type].write1ByteTxRx(
                    self.ports[arm_type], motor_id, ADDR_TORQUE_ENABLE, 0
                )
                self.motor_torque_enabled[arm_type][motor_name] = False
            else:
                # トルクON
                self.packet_handlers[arm_type].write1ByteTxRx(
                    self.ports[arm_type], motor_id, ADDR_TORQUE_ENABLE, 1
                )
                self.motor_torque_enabled[arm_type][motor_name] = True
            
            self.goal_labels[arm_type][motor_name].config(text=f"{current_pos:4d}")
            self.sliders[arm_type][motor_name].set(current_pos)
        
        if all_torque_enabled:
            self.torque_buttons[arm_type].config(text="All Torque OFF")
            self.torque_status_labels[arm_type].config(text="(Safe Mode)", foreground='green')
        else:
            self.torque_buttons[arm_type].config(text="All Torque ON")
            self.torque_status_labels[arm_type].config(text="(Active)", foreground='orange')
    
    def on_slider_change(self, arm_type, motor_name, value):
        """スライダー変更時の処理"""
        position = int(float(value))
        self.goal_labels[arm_type][motor_name].config(text=f"{position:4d}")
        
        if self.motor_torque_enabled[arm_type].get(motor_name, False):
            motor_id = self.config[arm_type]['calibration'][motor_name]['id']
            self.packet_handlers[arm_type].write2ByteTxRx(
                self.ports[arm_type], motor_id, ADDR_GOAL_POSITION, position
            )
    
    def update_loop(self):
        """位置更新"""
        while self.running:
            try:
                for arm_type in ['follower', 'leader']:
                    for motor_name in self.motor_order:
                        motor_id = self.config[arm_type]['calibration'][motor_name]['id']
                        position, _, _ = self.packet_handlers[arm_type].read2ByteTxRx(
                            self.ports[arm_type], motor_id, ADDR_PRESENT_POSITION
                        )
                        self.position_labels[arm_type][motor_name].config(text=f"{position:4d}")
                        
                        torque_status, _, _ = self.packet_handlers[arm_type].read1ByteTxRx(
                            self.ports[arm_type], motor_id, ADDR_TORQUE_ENABLE
                        )
                        self.motor_torque_enabled[arm_type][motor_name] = bool(torque_status)
                    
                    # トルクボタン表示更新
                    all_torque_enabled = all(self.motor_torque_enabled[arm_type].values())
                    if all_torque_enabled:
                        self.torque_buttons[arm_type].config(text="All Torque ON")
                        self.torque_status_labels[arm_type].config(text="(Active)", foreground='orange')
                    else:
                        self.torque_buttons[arm_type].config(text="All Torque OFF")
                        self.torque_status_labels[arm_type].config(text="(Safe Mode)", foreground='green')
                
                time.sleep(0.1)
            except Exception:
                break
    
    def signal_handler(self, signum, frame):
        """Ctrl+C時の処理"""
        print("\nCtrl+C が検出されました。停止中...")
        self.running = False
        self.stop_motors()
        self.root.quit()
        sys.exit(0)
    
    def stop_motors(self):
        """モーターを安全に停止"""
        try:
            for arm_type in ['follower', 'leader']:
                for motor_name in self.motor_order:
                    motor_id = self.config[arm_type]['calibration'][motor_name]['id']
                    current_pos, _, _ = self.packet_handlers[arm_type].read2ByteTxRx(
                        self.ports[arm_type], motor_id, ADDR_PRESENT_POSITION
                    )
                    self.packet_handlers[arm_type].write2ByteTxRx(
                        self.ports[arm_type], motor_id, ADDR_GOAL_POSITION, current_pos
                    )
                    self.packet_handlers[arm_type].write1ByteTxRx(
                        self.ports[arm_type], motor_id, ADDR_TORQUE_ENABLE, 0
                    )
                self.ports[arm_type].closePort()
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
        gui = DualRobotGUI()
        gui.run()
    except Exception as e:
        print(f"エラー: {e}")
        if gui:
            gui.stop_motors()

if __name__ == "__main__":
    main()
