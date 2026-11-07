"""Irrigation state machine and safety envelope.

All clients submit intents here.  The controller owns the relay, the maximum
run time, the minimum off time, the auto-mode interval and the fault latch.
"""

from sensors.base import is_stale

STATE_IDLE = "idle"
STATE_MANUAL = "manual"
STATE_AUTO = "auto"
STATE_COOLDOWN = "cooldown"
STATE_FAULT = "fault"


class IrrigationController:
    def __init__(self, relay, config, clock, state, history, logger):
        self.relay = relay
        self.config = config
        self.clock = clock
        self.state_store = state
        self.history = history
        self.logger = logger
        self.state = STATE_IDLE
        self.started_ts = None
        self.last_start_ts = None
        self.last_stop_ts = None
        self.last_action = None
        self._requests = {}
        self.publish(self.clock.now())

    @property
    def irrigation_config(self):
        return self.config.get("irrigation", {})

    @property
    def mode(self):
        return self.irrigation_config.get("mode", "auto")

    def set_mode(self, mode):
        if mode not in ("auto", "manual"):
            return False, "mode must be 'auto' or 'manual'"
        self.irrigation_config["mode"] = mode
        self.publish(self.clock.now())
        return True, None

    def can_start(self, now):
        cfg = self.irrigation_config
        if self.relay.fault:
            return False, "FAULT", "relay fault: %s" % self.relay.fault
        if self.relay.on:
            return False, "ALREADY_RUNNING", "pump is already running"
        min_off = int(cfg.get("min_off_s", 5))
        if self.last_stop_ts is not None and (now - self.last_stop_ts) < min_off:
            return False, "MIN_OFF", "minimum off time is %ss" % min_off
        return True, None, None

    def start(self, trigger, now):
        ok, code, message = self.can_start(now)
        if not ok:
            return {"ok": False, "code": code, "message": message}
        if not self.relay.set(True, trigger):
            self.state = STATE_FAULT
            self.publish(now)
            return {"ok": False, "code": "RELAY_FAILED", "message": "relay did not switch on"}
        self.started_ts = int(now)
        self.last_start_ts = int(now)
        self.state = STATE_MANUAL if trigger == "manual" else STATE_AUTO
        self.history.start(now, trigger)
        self.last_action = {"action": "start", "trigger": trigger, "ts": int(now)}
        self.logger.info("irrigation start (%s)", trigger)
        self.publish(now)
        return {"ok": True}

    def stop(self, reason, now):
        self.relay.off(reason)
        self.last_stop_ts = int(now)
        if self.state not in (STATE_FAULT,):
            self.state = STATE_COOLDOWN
        self.history.stop(now, reason)
        self.last_action = {"action": "stop", "reason": reason, "ts": int(now)}
        self.logger.info("irrigation stop (%s)", reason)
        self.publish(now)
        return {"ok": True}

    def tick(self, now, soil_reading):
        cfg = self.irrigation_config
        if self.relay.on:
            elapsed = int(now) - int(self.started_ts or now)
            if elapsed >= int(cfg.get("max_run_s", 20)):
                self.stop("max_run", now)
                return
        else:
            if self.state == STATE_COOLDOWN:
                if self.last_stop_ts is None or (now - self.last_stop_ts) >= int(cfg.get("min_off_s", 5)):
                    self.state = STATE_IDLE

        if self.mode != "auto" or self.state != STATE_IDLE or self.relay.on:
            self.publish(now)
            return

        stale_s = int(cfg.get("sensor_stale_s", 90))
        if soil_reading is None or not soil_reading.valid or is_stale(soil_reading, now, stale_s):
            self.publish(now)
            return

        threshold = float(cfg.get("soil_threshold", 35.0))
        hysteresis = float(cfg.get("hysteresis", 3.0))
        if soil_reading.value >= threshold - hysteresis:
            self.publish(now)
            return

        min_interval = int(cfg.get("min_interval_s", 1800))
        if self.last_stop_ts is not None and (now - self.last_stop_ts) < min_interval:
            self.publish(now)
            return

        self.start("auto", now)

    def request(self, action, source, request_id, now):
        """Handle a client intent.  Idempotent for 60 seconds per request id."""
        if request_id:
            cached = self._requests.get(request_id)
            if cached and (now - cached["ts"]) <= 60:
                return cached["result"]
        if action == "start":
            result = self.start(source, now)
        elif action == "stop":
            if not self.relay.on:
                result = {"ok": True, "already": "stopped"}
            else:
                result = self.stop("manual_stop", now)
        else:
            result = {"ok": False, "code": "BAD_ACTION", "message": "action must be 'start' or 'stop'"}
        if request_id:
            self._requests[request_id] = {"ts": int(now), "result": result}
            if len(self._requests) > 50:
                oldest = sorted(self._requests.items(), key=lambda item: item[1]["ts"])[0][0]
                self._requests.pop(oldest, None)
        return result

    def clear_fault(self):
        self.relay.fault = None
        self.state = STATE_IDLE
        self.publish(self.clock.now())

    def publish(self, now):
        cfg = self.irrigation_config
        if self.relay.on and self.started_ts is not None:
            remaining = max(0, int(cfg.get("max_run_s", 20)) - (int(now) - int(self.started_ts)))
        else:
            remaining = 0
        if self.relay.fault:
            self.state = STATE_FAULT
        payload = {
            "mode": self.mode,
            "pump": bool(self.relay.on),
            "state": self.state,
            "remaining_s": remaining,
            "last_start_ts": self.last_start_ts,
            "last_stop_ts": self.last_stop_ts,
            "max_run_s": int(cfg.get("max_run_s", 20)),
            "threshold": float(cfg.get("soil_threshold", 35.0)),
            "min_interval_s": int(cfg.get("min_interval_s", 1800)),
            "history": self.history.recent(10),
            "last_action": self.last_action,
        }
        self.state_store.set_irrigation(payload)
        return payload
