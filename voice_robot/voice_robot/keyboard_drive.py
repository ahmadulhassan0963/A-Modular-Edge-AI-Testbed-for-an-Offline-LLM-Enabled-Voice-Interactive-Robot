#!/usr/bin/env python3
import sys
import termios
import tty
import serial

PORT = "/dev/ttyACM0"
BAUD = 9600

KEY_TO_CMD = {
    "w": "F",
    "s": "B",
    "a": "L",
    "d": "R",
    " ": "S",
}


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def main():
    arduino = serial.Serial(PORT, BAUD, timeout=1)
    print("Connected to Arduino on", PORT)
    print("w=forward  s=back  a=left  d=right  space=stop  q=quit")

    try:
        while True:
            key = get_key().lower()
            if key == "q":
                arduino.write(b"S")
                print("Quit")
                break
            if key in KEY_TO_CMD:
                cmd = KEY_TO_CMD[key]
                arduino.write(cmd.encode())
                print("Sent:", cmd)
    except KeyboardInterrupt:
        arduino.write(b"S")
    finally:
        arduino.write(b"S")
        arduino.close()


if __name__ == "__main__":
    main()
