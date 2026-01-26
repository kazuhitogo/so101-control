# SO101 Control

Feetech-Servo-SDKを使って直接SO101ロボットアームを制御する実装例です。

## 概要

このプロジェクトは、SO101ロボットアームをスクラッチで制御するためのツール群です。LeRobot のようなラッパーを使わず、サーボモーターの制御を直接理解しながら操作できます。

主な機能：
- USBポートの自動検索
- モーターIDの設定と確認
- キャリブレーション（ホーミングオフセット設定）
- GUI/MCPサーバーによるモーター制御

## セットアップ

### 1. パッケージのインストール

プロジェクトルートで以下を実行：

```bash
pip install -e .
```

### 2. ポート検索

ロボットアームをUSBで接続し、シリアルポートを特定します：

```bash
python 01_search_port.py
```

出力例：
```
['/dev/tty.usbmodem5AB90678311', '/dev/tty.usbmodem5AB90669381']
```

どちらがフォロワー/リーダーアームかを確認し、`.env.yaml`に記録します：

```yaml
follower:
  port: "/dev/tty.usbmodem5AB90678311"
leader:
  port: "/dev/tty.usbmodem5AB90669381"
```

### 3. モーターIDの設定

各モーターに論理名に紐づくIDをEEPROMに書き込みます：

```bash
python 02_setup_motors.py
```

モーターを1つずつドライバーに接続し、以下の順番でIDを設定します：
- gripper (ID: 6)
- wrist_roll (ID: 5)
- wrist_flex (ID: 4)
- elbow_flex (ID: 3)
- shoulder_lift (ID: 2)
- shoulder_pan (ID: 1)

### 4. ID確認

設定したIDが正しく書き込まれているか確認します：

```bash
python 03_identify_motors.py
```

### 5. キャリブレーション

各モーターの可動範囲とホーミングオフセットを設定します：

```bash
python 04_calibrate.py
```

キャリブレーションの流れ：
1. 各モーターを中間位置に配置
2. オフセットを設定して位置を2047に調整
3. モーターを限界まで動かして最小値・最大値を記録

結果は`.env.yaml`に自動保存されます。

### 6. 動作確認

GUIでモーターを動かして動作確認：

```bash
python 05_check.py
```

## ファイル構成

### メインスクリプト

- **`01_search_port.py`** - USB接続されたサーボモーターのポートを自動検索
- **`02_setup_motors.py`** - モーターIDの初期設定とセットアップ
- **`03_identify_motors.py`** - 接続されているモーターのIDを読み取り・確認
- **`04_calibrate.py`** - モーターのキャリブレーション（ホーミングオフセット設定）
- **`05_check.py`** - モーターの動作確認とテスト（GUI）

### MCPサーバー

- **`agent/so101.py`** - Model Context Protocol (MCP)サーバー。LLMからfunction callingでモーターを制御可能

### 設定ファイル

- **`servo_constants.py`** - サーボモーター制御用の定数定義（プロトコル、レジスタアドレス、モーター構成）
- **`.env.yaml`** - ロボット設定（ポート、キャリブレーション値）
- **`pyproject.toml`** - Pythonプロジェクト設定と依存関係

## 技術詳細

### サーボモーター制御

Feetech STS3215サーボモーターを使用。主な制御方法：

- **位置制御**: `write2ByteTxRx`で目標位置（0-4095）を指定
- **PIDパラメータ**: P=16, I=0, D=32（LeRobotと同じ値を使用）
- **オペレーティングモード**: 位置制御モード（0）
- **トルク有効化**: `ADDR_TORQUE_ENABLE`に1を書き込み

### EEPROMメモリマップ

主要なアドレス：
- ID: 5
- ホーミングオフセット: 31（-2047〜2047の範囲）
- P/D/Iゲイン: 21/22/23
- トルク有効化: 40
- 目標位置: 42
- 現在位置: 56

## 参考記事

- [SO101のフォロワーアームをLeRobotを使わずに操作してみる](https://note.com/kazuhitogo/n/nba3989cfde9f)
- [ロボットアーム(SO101)を印刷して組み立てる](https://note.com/kazuhitogo/n/n62c458499109)
