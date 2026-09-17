#!/usr/bin/env python3
import os
import json
import queue

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH = os.path.expanduser("~/models/vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000


class STTNode(Node):
    def __init__(self):
        super().__init__("stt_node")
        self.pub = self.create_publisher(String, "voice_text", 10)

        self.get_logger().info(f"Loading Vosk model from {MODEL_PATH} ...")
        self.model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.audio_q = queue.Queue()

        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._audio_cb,
        )
        self.stream.start()
        self.get_logger().info("Listening... speak into the mic.")

        self.create_timer(0.01, self._process_audio)

    def _audio_cb(self, indata, frames, time, status):
        if status:
            self.get_logger().warn(str(status))
        self.audio_q.put(bytes(indata))

    def _process_audio(self):
        try:
            data = self.audio_q.get_nowait()
        except queue.Empty:
            return
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                self.get_logger().info(f"Heard: {text}")
                self.pub.publish(String(data=text))


def main():
    rclpy.init()
    node = STTNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stream.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
