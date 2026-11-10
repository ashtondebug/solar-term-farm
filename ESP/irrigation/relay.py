"""The only module allowed to touch the relay GPIO.

Hardware contract: 3.3V active-high module on GPIO5.
    HIGH (3.3V) -> relay energised -> pump runs
    LOW  (0V)   -> relay released -> pump stops

The constructor drives the pin LOW before anything else.  The external
pull-down and COM/NO wiring remain the primary fail-safe; this class is the
software layer that must never invert the polarity.

An optional auxiliary contact can be wired to a GPIO input.  It closes when
the relay is energised and is used to detect a failed coil/contact; without
that feedback the firmware can only verify the GPIO level, not the contact.
"""

import time


class Relay:
    def __init__(
        self,
        pin,
        active_high=True,
        logger=None,
        feedback_pin=None,
        feedback_active_low=True,
    ):
        self.pin = pin
        self.active_high = bool(active_high)
        self.logger = logger
        self.feedback_pin = feedback_pin
        self.feedback_active_low = bool(feedback_active_low)
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

    def _settle(self):
        try:
            time.sleep_ms(20)
        except AttributeError:
            time.sleep(0.02)

    def feedback_closed(self):
        if self.feedback_pin is None:
            return None
        try:
            value = 1 if self.feedback_pin.value() else 0
        except Exception as exc:
            self.fault = "feedback_gpio_error: %s" % exc
            if self.logger:
                self.logger.error("relay feedback read failed: %s", exc)
            return None
        return bool(value) if not self.feedback_active_low else not bool(value)

    def _feedback_matches(self, expected):
        actual = self.feedback_closed()
        if actual is None or actual == expected:
            return True
        self.fault = "relay_feedback_mismatch: expected %s actual %s" % (
            "on" if expected else "off",
            "on" if actual else "off",
        )
        if self.logger:
            self.logger.error(self.fault)
        return False

    def set(self, on, reason=""):
        if on and self.fault:
            return False
        if not self._apply(on):
            self.on = False
            return False
        self.on = bool(on)
        if self.feedback_pin is not None:
            self._settle()
            if not self._feedback_matches(self.on):
                # Failed to energise: try to return the output to safe off.
                if self.on:
                    self._apply(False)
                    self.on = False
                return False
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
            "feedback": self.feedback_closed(),
        }

