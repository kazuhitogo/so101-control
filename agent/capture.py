from mcp.server.fastmcp import FastMCP
import cv2
from uuid import uuid4
import os

mcp = FastMCP("WebCam")

@mcp.tool()
def capture():
    """
    Web カメラで撮影して撮影した画像のファイルパスを返す

    Args:
        None

    Returns:
        ファイルパス
    """
    cap = cv2.VideoCapture(0)
    
    ret, frame = cap.read()
    cap.release()
    
    file_name = os.path.join("capture",f"{uuid4()}.jpg")
    cv2.imwrite(file_name, frame)
    
    return file_name
    
if __name__ == "__main__":
    mcp.run(transport="stdio")