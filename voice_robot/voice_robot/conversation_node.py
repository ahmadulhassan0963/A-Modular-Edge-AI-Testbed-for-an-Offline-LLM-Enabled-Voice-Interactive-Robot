#!/usr/bin/env python3
"""conversation_node.py — LLM chat + motors, with latency logging."""

import time
import threading
import subprocess
import os

import requests
import serial

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

PORT = "/dev/ttyACM0"
BAUD = 9600
MOVE_TIMEOUT = 2.0
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"
PIPER_MODEL = os.path.expanduser("~/piper_voices/en_US-lessac-medium.onnx")

SYSTEM_PROMPT = (
    "You are a voice robot assistant. Answer in one short sentence, "
    "directly and to the point. Give only the answer asked for. No lists."
)
NOISE = {"huh", "uh", "um", "hmm", "eh", "ah", "the", "a", "oh", "mm", "hm", "err"}


class ConversationNode(Node):
    def __init__(self):
        super().__init__("conversation_node")
        self.arduino = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2.0)
        self.send_motor("S")
        self.get_logger().info(f"Connected to Arduino on {PORT}")
        self.current_audio = None
        self.audio_lock = threading.Lock()
        self.busy = False
        self.create_subscription(String, "voice_text", self.on_voice, 10)
        self.last_move = None
        self.create_timer(0.1, self.safety_check)
        self.get_logger().info("Conversation node ready.")

    def say(self, text):
        if not text:
            return
        wav = "/tmp/convo.wav"
        try:
            piper = subprocess.Popen(["piper", "--model", PIPER_MODEL,
                                      "--output_file", wav], stdin=subprocess.PIPE)
            piper.communicate(input=text.encode())
            with self.audio_lock:
                self.current_audio = subprocess.Popen(["aplay", "-q", wav])
            self.current_audio.wait()
            with self.audio_lock:
                self.current_audio = None
        except Exception as e:
            print("TTS error:", e)

    def stop_audio(self):
        with self.audio_lock:
            if self.current_audio and self.current_audio.poll() is None:
                self.current_audio.terminate()
            self.current_audio = None

    def send_motor(self, letter):
        self.arduino.write(letter.encode())

    def safety_check(self):
        if self.last_move is None:
            return
        if time.time() - self.last_move >= MOVE_TIMEOUT:
            self.send_motor("S")
            self.last_move = None

    def on_voice(self, msg):
        t_start = time.time()          # command arrives
        text = msg.data.lower().strip()
        if not text or text in NOISE or len(text) < 3:
            return
        if "read" in text or "narrate" in text:
            return
        if "stop" in text or "halt" in text:
            self.busy = False
            self.stop_audio()
            self.send_motor("S"); self.last_move = None
            return
        if self.busy:
            return

        # MOTION latency: command -> GPIO letter sent
        motion = None
        if "forward" in text or "go ahead" in text:
            motion = "F"
        elif "reverse" in text or "go back" in text:
            motion = "B"
        elif "left" in text:
            motion = "L"
        elif "right" in text:
            motion = "R"
        if motion:
            self.send_motor(motion)
            self.last_move = time.time()
            self.get_logger().info(
                f"LATENCY motion: {time.time() - t_start:.3f} s")
            return

        # QUESTION latency handled in the thread
        threading.Thread(target=self.ask_llm, args=(text, t_start),
                         daemon=True).start()

    def ask_llm(self, text, t_start):
        self.busy = True
        try:
            r = requests.post(OLLAMA_URL, json={
                "model": MODEL, "prompt": text, "system": SYSTEM_PROMPT,
                "stream": False, "options": {"num_predict": 60},
            }, timeout=60)
            reply = r.json().get("response", "").strip()
            # latency = question arrival -> answer ready to speak
            self.get_logger().info(
                f"LATENCY question_to_answer: {time.time() - t_start:.3f} s")
            self.say(reply if reply else "Sorry, I did not catch that.")
        except Exception as e:
            self.get_logger().error(f"LLM error: {e}")
            self.say("Sorry, my brain is not responding.")
        finally:
            self.busy = False

    def destroy_node(self):
        try:
            self.stop_audio()
            self.send_motor("S")
            self.arduino.close()
        except Exception:
            pass
        super().destroy_node()


def main():
    rclpy.init()
    node = ConversationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
