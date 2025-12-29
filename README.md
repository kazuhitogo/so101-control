# SO101 Control

SO101ロボットアーム制御システム - Feetechサーボモーターを使用したロボットアーム制御用のPythonツール群

## ファイル構成

### メインスクリプト

- **`01_search_port.py`** - USB接続されたサーボモーターのポートを自動検索
- **`02_setup_motors.py`** - モーターIDの初期設定とセットアップ
- **`03_identify_motors.py`** - 接続されているモーターのIDを読み取り・確認
- **`04_calibrate.py`** - モーターのキャリブレーション（ホーミングオフセット設定）
- **`05_check.py`** - モーターの動作確認とテスト

### 設定ファイル

- **`servo_constants.py`** - サーボモーター制御用の定数定義（プロトコル、レジスタアドレス、モーター構成）
- **`.env.yaml`** - ロボット設定（ポート、キャリブレーション値）
- **`pyproject.toml`** - Pythonプロジェクト設定と依存関係

## 使用手順

1. **ポート検索**: `python 01_search_port.py`
2. **モーター設定**: `python 02_setup_motors.py`
3. **ID確認**: `python 03_identify_motors.py`
4. **キャリブレーション**: `python 04_calibrate.py`
5. **動作確認**: `python 05_check.py`

## 依存関係

- feetech-servo-sdk
- pyserial
- pyyaml
- black (コードフォーマット用)
