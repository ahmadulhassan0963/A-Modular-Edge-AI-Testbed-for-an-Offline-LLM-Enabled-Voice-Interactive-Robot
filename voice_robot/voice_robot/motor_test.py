#!/usr/bin/env python3
import time
import Jetson.GPIO as GPIO

IN1, IN2, IN3, IN4 = 29, 31, 33, 35

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
for pin in (IN1, IN2, IN3, IN4):
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

def all_off():
    for pin in (IN1, IN2, IN3, IN4):
        GPIO.output(pin, GPIO.LOW)

try:
    print("Motor A (IN1/IN2) forward for 2 seconds...")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(2)
    all_off()
    time.sleep(1)

    print("Motor B (IN3/IN4) forward for 2 seconds...")
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    time.sleep(2)
    all_off()
    time.sleep(1)

    print("Both motors forward for 3 seconds...")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    time.sleep(3)
    all_off()

    print("Test finished.")
finally:
    all_off()
    GPIO.cleanup()
    print("GPIO cleaned up.")
