from strands import Agent, tool
import cv2
from uuid import uuid4
import os

@tool()
def capture():
    """Web カメラで撮影して撮影した画像のファイルパスを返す"""
    cap = cv2.VideoCapture(1) # WebCam を利用
    _, frame = cap.read()
    file_name = os.path.join("capture",f"{uuid4()}.jpg")
    cv2.imwrite(file_name, frame)
    cap.release()
    
    return file_name

if __name__ == "__main__":
    agent = Agent(
        system_prompt="あなたはユーザーに忠実なエージェントです。",
        tools=[capture],
        model = "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        # model = "global.anthropic.claude-opus-4-5-20251101-v1:0",
    )
    agent("Webカメラで撮影して何が写っているか教えて")