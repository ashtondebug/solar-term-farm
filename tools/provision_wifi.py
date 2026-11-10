#!/usr/bin/env python3
"""Prompt locally for Wi-Fi credentials and write them to the board.

The password is read with getpass, never printed and never sent through chat.
This script uses the serial REPL directly instead of mpremote so the device
watchdog cannot interrupt the upload. It writes ``/data/wifi.json``, restores
``main.py``, resets, and reads the resulting IP from the serial log.
"""

import argparse
import base64
import getpass
import json
import time

import serial


def _drain(ser):
    try:
        return ser.read(ser.in_waiting or 1)
    except Exception:
        return b""


def _prompt(ser):
    for _ in range(20):
        ser.write(b"\x03")
        time.sleep(0.25)
        if b">>>" in _drain(ser):
            return True
    return False


def _cmd(ser, text, wait=0.05):
    ser.write(text.encode("ascii") + b"\r\n")
    time.sleep(wait)
    _drain(ser)


def _reset(ser, wait_s=5):
    _cmd(ser, "import machine; machine.reset()", 0.2)
    time.sleep(wait_s)
    return _prompt(ser)


def upload(port, ssid, password):
    payload = json.dumps({"ssid": ssid, "password": password}, ensure_ascii=False).encode("utf-8")
    encoded = base64.b64encode(payload).decode("ascii")
    ser = serial.Serial(port, 115200, timeout=0.25, write_timeout=1)
    try:
        if not _prompt(ser):
            raise SystemExit("no serial REPL prompt")
        _cmd(ser, "import os")
        try:
            _cmd(ser, "os.rename('main.py','main.bak')")
        except Exception:
            pass
        if not _reset(ser):
            raise SystemExit("no REPL after disabling main")
        _cmd(ser, "import os")
        _cmd(ser, "os.mkdir('data')")
        _cmd(ser, "import binascii")
        _cmd(ser, "f=open('/data/wifi.json','wb')")
        for index in range(0, len(encoded), 160):
            _cmd(ser, "f.write(binascii.a2b_base64('%s'))" % encoded[index:index + 160], 0.03)
        _cmd(ser, "f.close()")
        _cmd(ser, "os.rename('main.bak','main.py')")
        _cmd(ser, "import machine; machine.reset()", 0.2)
        time.sleep(2)
    finally:
        ser.close()


def read_until_ip(port, timeout_s):
    ser = serial.Serial(port, 115200, timeout=0.5)
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
            if "wifi connected:" in buffer:
                return
            if "wrong_password" in buffer:
                print("\nWi-Fi password rejected. Re-run the script.")
                return
            if "no_ap_found" in buffer:
                print("\nWi-Fi SSID not found. Check the hotspot name.")
                return
            if "provisioning" in buffer:
                print("\nDevice entered provisioning after repeated failures.")
                return
    finally:
        ser.close()
    print("\nNo IP observed before timeout; check the serial log.")


def main():
    parser = argparse.ArgumentParser(description="Upload Wi-Fi credentials to AgriVerse")
    parser.add_argument("--port", default="COM11", help="serial port, e.g. COM11")
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

    upload(args.port, ssid, password)
    print("credentials uploaded; waiting for Wi-Fi")
    if not args.no_wait:
        read_until_ip(args.port, args.timeout)


if __name__ == "__main__":
    main()
