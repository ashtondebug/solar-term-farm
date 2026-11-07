"""The only module allowed to touch the relay GPIO.

Hardware contract: 3.3V active-high module on GPIO5.
    HIGH (3.3V) -> relay energised -> pump runs
    LOW  (0V)   -> relay released -> pump stops

The constructor drives the pin LOW before anything else.  The external
pull-down and COM/NO wiring remain the primary fail-safe; this class is the
software layer that must never invert the polarity.
"""


class Relay:
    def __init__(self, pin, active_high=True, logger=None):
        self.pin = pin
        self.active_high = bool(active_high)
        self.logger = logger
        self.on = False
        self.fault = None
        self._apply(False)

    def _level(self, on):
        return 1 if (bool(on) == self.active_high) else 0

    def _apply(self, on):
        try:
            self.pin.value(self._level(on))
            return True
        except Exception as exc:
            self.fault = "gpio_error: %s" % exc
            if self.logger:
                self.logger.error("relay write failed: %s", exc)
            return False

    def set(self, on, reason=""):
        if on and self.fault:
            return False
        if not self._apply(on):
            self.on = False
            return False
        self.on = bool(on)
        if self.logger:
            self.logger.info("pump %s (%s)", "on" if self.on else "off", reason or "no-reason")
        return True

    def off(self, reason=""):
        return self.set(False, reason)

    def status(self):
        return {
            "on": self.on,
            "active_high": self.active_high,
            "fault": self.fault,
        }
