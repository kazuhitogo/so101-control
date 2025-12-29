from pathlib import Path

ports = [str(path) for path in Path("/dev").glob("tty.usbmodem*")]
print(ports)
