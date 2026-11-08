#!/usr/bin/env python3
"""Prompt locally for Wi-Fi credentials and write them to the board.

The password is read with getpass, never printed, never passed through the
chat, and only written to a temporary file that is uploaded to
``/data/wifi.json`` and then deleted. After reset the script reads the serial
log to show the IP address (or the failure reason).
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile
import time


def run(command):
    print("+ " + " ".join(command))
    code = subprocess.call(command)
    if code != 0:
        raise SystemExit("command failed: %s" % " ".join(command))


def read_until_ip(port, timeout_s):
    try:
        import serial
    except ImportError:
        print("pyserial is not available; check the serial log manually.")
        return
    time.sleep(1.5)
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 1
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
        ser.reset_input_buffer()
    except Exception as exc:
        print("serial open failed: %s" % exc)
        return
    print("waiting for Wi-Fi (up to %ss)..." % timeout_s)
    deadline = time.time() + timeout_s
    buffer = ""
    try:
        while time.time() < deadline:
            data = ser.read(256)
            if not data:
                continue
            text = data.decode("utf-8", "replace")
            print(text, end="")
            buffer += text
            if "wifi connected:" in buffer or "192.168." in buffer:
                return
            if "wrong_password" in buffer:
                print("\nWi-Fi password rejected (wrong_password). Re-run the script.")
                return
            if "no_ap_found" in buffer:
                print("\nWi-Fi SSID not found (no_ap_found). Check the SSID.")
                return
            if "provisioning" in buffer:
                print("\nFive attempts failed; device entered provisioning.")
                return
    finally:
        ser.close()
    print("\nNo IP seen before timeout; check the serial log or router.")


def main():
    parser = argparse.ArgumentParser(description="Upload Wi-Fi credentials to AgriVerse")
    parser.add_argument("--port", default="COM10", help="serial port, e.g. COM10")
    parser.add_argument("--timeout", type=int, default=60, help="seconds to wait for IP")
    parser.add_argument("--no-wait", action="store_true", help="do not read the serial log")
    args = parser.parse_args()

    ssid = input("Wi-Fi SSID: ").strip()
    if not ssid:
        raise SystemExit("SSID is required")
    if len(ssid) > 32:
        raise SystemExit("SSID is too long (max 32)")
    password = getpass.getpass("Wi-Fi password (hidden): ")
    if len(password) > 64:
        raise SystemExit("password is too long (max 64)")

    fd, path = tempfile.mkstemp(prefix="agri-wifi-", suffix=".json")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"ssid": ssid, "password": password}, handle, ensure_ascii=False)
        print("+ mpremote connect %s fs mkdir :data" % args.port)
        subprocess.call(["mpremote", "connect", args.port, "fs", "mkdir", ":data"])
        run(["mpremote", "connect", args.port, "fs", "cp", path, ":data/wifi.json"])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    print("credentials uploaded; resetting board")
    run(["mpremote", "connect", args.port, "reset"])
    if not args.no_wait:
        read_until_ip(args.port, args.timeout)


if __name__ == "__main__":
    main()
