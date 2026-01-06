from pathlib import Path

ports = [str(path) for path in Path("/dev").glob("tty.usbmodem*")]
print("検出されたポート:", ports)
