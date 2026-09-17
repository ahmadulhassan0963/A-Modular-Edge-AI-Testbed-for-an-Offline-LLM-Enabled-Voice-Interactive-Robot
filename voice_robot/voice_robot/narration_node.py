#!/usr/bin/env python3
"""narration_node.py — PDF reading only, with start-up latency logging."""

import os
import re
import glob
import time
import threading
import subprocess

import fitz
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

PIPER_MODEL = os.path.expanduser("~/piper_voices/en_US-lessac-medium.onnx")
PDF_DIR = os.path.expanduser("~/voice_robot_ws/Pdf")
TRIGGER_WORDS = {"read", "narrate", "the", "pdf", "please", "start", "reading"}


def normalize(s):
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


class NarrationNode(Node):
    def __init__(self):
        super().__init__("narration_node")
        self.current_audio = None
        self.audio_lock = threading.Lock()
        self.reading = False
        self.stop_reading = False
        self.create_subscription(String, "voice_text", self.on_voice, 10)
        self.get_logger().info("Narration node ready.")

    def say(self, text):
        if not text or self.stop_reading:
            return
        wav = "/tmp/narration.wav"
        try:
            piper = subprocess.Popen(["piper", "--model", PIPER_MODEL,
                                      "--output_file", wav], stdin=subprocess.PIPE)
            piper.communicate(input=text.encode())
            if self.stop_reading:
                return
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

    def find_pdf(self, text):
        pdfs = glob.glob(os.path.join(PDF_DIR, "*.pdf")) + glob.glob(os.path.join(PDF_DIR, "*.PDF"))
        if not pdfs:
            return None, []
        words = [w for w in text.split() if w not in TRIGGER_WORDS]
        query = normalize(" ".join(words))
        for path in pdfs:
            stem = normalize(os.path.splitext(os.path.basename(path))[0])
            if query and (query in stem or stem in query):
                return path, pdfs
            for w in words:
                if len(w) >= 3 and normalize(w) in stem:
                    return path, pdfs
        return None, pdfs

    def read_book(self, path, t_start):
        try:
            doc = fitz.open(path)
        except Exception as e:
            self.get_logger().error(f"PDF error: {e}")
            return
        self.reading = True
        first = True
        for i in range(len(doc)):
            if self.stop_reading:
                break
            page = doc.load_page(i).get_text().strip()
            if not page:
                continue
            for sentence in split_sentences(page):
                if self.stop_reading:
                    break
                if first:
                    # latency = command -> first spoken sentence
                    self.get_logger().info(
                        f"LATENCY narration_startup: {time.time() - t_start:.3f} s")
                    first = False
                self.say(sentence)
        self.reading = False

    def on_voice(self, msg):
        t_start = time.time()
        text = msg.data.lower().strip()
        if not text:
            return
        if "stop" in text or "halt" in text:
            self.stop_reading = True
            self.stop_audio()
            return
        if self.reading:
            return
        if "read" in text or "narrate" in text:
            match, pdfs = self.find_pdf(text)
            if match is None:
                if pdfs:
                    names = ", ".join(os.path.splitext(os.path.basename(p))[0] for p in pdfs)
                    self.say(f"I could not find that book. I have: {names}")
                return
            self.stop_reading = False
            threading.Thread(target=self.read_book, args=(match, t_start),
                             daemon=True).start()


def main():
    rclpy.init()
    node = NarrationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_reading = True
        node.stop_audio()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
