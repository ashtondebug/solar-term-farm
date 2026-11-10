#!/usr/bin/env python3
"""Safe manual relay-fault injection test for a real SolarTerm Farm device.

This script does NOT fake a fault in firmware.  It starts a short pump cycle,
asks the operator to physically interrupt the relay control path, and records
what the device reports.  That distinguishes two questions:

1. Does the relay de-energise and stop the pump when control is lost?
2. Does the device detect and latch that fault?

The current hardware has no relay aux contact/current feedback, so question 2
is expected to be NO.  Do not leave the pump unattended.

Usage:
    python tools/relay_fault_test.py --base-url http://DEVICE_IP \
        --confirm RUN_RELAY_FAULT_TEST
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid


def call(base, path, method="GET", body=None, pin=None, timeout=6):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if pin:
        req.add_header("X-AgriVerse-Pin", pin)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"code": "HTTP", "message": str(exc)}}
        return exc.code, payload


def state(base, pin):
    return call(base, "/api/v1/state", pin=pin)[1].get("data", {})


def irrigation(base, pin):
    return state(base, pin).get("irrigation") or {}


def show(label, value):
    print("%-24s %s" % (label, value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="e.g. http://192.168.1.50")
    parser.add_argument("--confirm", required=True, help="must be RUN_RELAY_FAULT_TEST")
    parser.add_argument("--pin", default=os.environ.get("AGRI_PIN"))
    parser.add_argument("--wait", type=float, default=4.0, help="seconds after injection")
    args = parser.parse_args()
    if args.confirm != "RUN_RELAY_FAULT_TEST":
        raise SystemExit("refusing to run without --confirm RUN_RELAY_FAULT_TEST")

    status, body = call(args.base_url, "/api/v1/health", pin=args.pin)
    show("health", "%s %s" % (status, body))
    if status != 200:
        raise SystemExit("device health is not reachable")

    before = irrigation(args.base_url, args.pin)
    show("before.pump", before.get("pump"))
    show("before.state", before.get("state"))
    if before.get("pump"):
        raise SystemExit("pump is already on; stop it before the test")

    request_id = "relay-fault-%s" % uuid.uuid4().hex[:8]
    status, body = call(
        args.base_url,
        "/api/v1/irrigation/commands",
        method="POST",
        body={"action": "start", "request_id": request_id},
        pin=args.pin,
    )
    show("start", "%s %s" % (status, body.get("ok")))
    if status != 200 or not body.get("data", {}).get("irrigation", {}).get("pump"):
        call(
            args.base_url,
            "/api/v1/irrigation/commands",
            method="POST",
            body={"action": "stop", "request_id": request_id + "-stop"},
            pin=args.pin,
        )
        raise SystemExit("pump did not start; aborted")

    try:
        print()
        print(">>> FAULT INJECTION WINDOW <<<")
        print("With the pump running, physically disconnect ONE of:")
        print("  A) relay IN signal from GPIO5")
        print("  B) relay coil VCC/GND (preferred for electrical fail-safe test)")
        print("Watch the pump and keep hands clear of mains/water.")
        input("Press Enter after the relay/pump has been disconnected: ")

        time.sleep(max(0.0, args.wait))
        after = irrigation(args.base_url, args.pin)
        show("after.pump", after.get("pump"))
        show("after.state", after.get("state"))
        show("after.alarm", after.get("alarm"))

        print()
        print("Expected observations:")
        print("  Electrical fail-safe: pump stops because the relay de-energises.")
        print("  Current firmware: NO feedback, so pump may still report ON until max_run.")
        print("  A real fault-detection result requires an aux contact or current sensor.")
    finally:
        call(
            args.base_url,
            "/api/v1/irrigation/commands",
            method="POST",
            body={"action": "stop", "request_id": request_id + "-cleanup"},
            pin=args.pin,
        )
        print("cleanup stop sent")


if __name__ == "__main__":
    main()
