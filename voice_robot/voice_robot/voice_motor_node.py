#!/usr/bin/env python3
"""
voice_motor_node.py — bridge /voice_text to the Arduino motor controller.
Maps spoken words to a letter (F/B/L/R/S) and sends it over USB serial.
Auto-stops after a couple of seconds so the robot never runs away.
"""

import time
import serial

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

PORT = "/dev/ttyACM0"
BAUD = 9600
MOVE_TIMEOUT = 2.0   # auto-stop this many seconds after a move command


class VoiceMotorNode(Node):
    def __init__(self):
        super().__init__("voice_motor_node")

        self.arduino = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2.0)  # give the Arduino a moment to reset
        self.get_logger().info(f"Connected to Arduino on {PORT}")

        self.sub = self.create_subscription(
            String, "voice_text", self.on_voice_text, 10)

        self.last_move_time = None
        self.create_timer(0.1, self.safety_check)

        self.send("S")
        self.get_logger().info("Voice motor node ready. Waiting for /voice_text ...")

    def send(self, letter):
        self.arduino.write(letter.encode())

    def on_voice_text(self, msg):
        text = msg.data.lower().strip()
        self.get_logger().info(f"Heard: {text}")

        if "forward" in text or "go ahead" in text:
            cmd = "F"
        elif "back" in text or "reverse" in text:
            cmd = "B"
        elif "left" in text:
            cmd = "L"
        elif "right" in text:
            cmd = "R"
        elif "stop" in text or "halt" in text:
            cmd = "S"
        else:
            self.get_logger().info("No movement word found")
            return

        self.send(cmd)
        self.get_logger().info(f"Sent to Arduino: {cmd}")
        self.last_move_time = None if cmd == "S" else time.time()

    def safety_check(self):
        if self.last_move_time is None:
            return
        if time.time() - self.last_move_time >= MOVE_TIMEOUT:
            self.send("S")
            self.last_move_time = None
            self.get_logger().info("Safety stop (timeout)")

    def destroy_node(self):
        try:
            self.send("S")
            self.arduino.close()
        except Exception:
            pass
        super().destroy_node()


def main():
    rclpy.init()
    node = VoiceMotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
