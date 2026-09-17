#!/usr/bin/env python3
"""
tts_node.py — Text-to-speech (the robot's voice).
Subscribes to /speech and speaks any text it receives, using Piper (offline).
Test (no mic needed, just a speaker/headphones):
    ros2 topic pub --once /speech std_msgs/msg/String "{data: 'hello, I am your robot'}"
"""

import os
import wave
import tempfile
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from piper import PiperVoice

MODEL_PATH = os.path.expanduser("~/models/piper/en_US-lessac-medium.onnx")


class TTSNode(Node):
    def __init__(self):
        super().__init__("tts_node")
        self.get_logger().info(f"Loading Piper voice from {MODEL_PATH} ...")
        self.voice = PiperVoice.load(MODEL_PATH)
        self.sub = self.create_subscription(String, "speech", self._on_text, 10)
        self.get_logger().info("Ready. Waiting for text on /speech ...")

    def _on_text(self, msg):
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f"Speaking: {text}")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            with wave.open(wav_path, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file)
            subprocess.run(["aplay", wav_path], check=False)
        finally:
            os.remove(wav_path)


def main():
    rclpy.init()
    node = TTSNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
