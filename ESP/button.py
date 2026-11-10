"""Active-high push button that toggles one irrigation cycle.

The button is an intent source only: it calls IrrigationController.request().
It never toggles the relay directly, so max_run/min_off/fault protection stays
authoritative. Press once to start, press again to stop.
"""

import asyncio


class PumpButton:
    def __init__(
        self,
        pin,
        controller,
        clock,
        logger,
        active_high=True,
        debounce_ms=50,
        request_prefix="button",
    ):
        self.pin = pin
        self.controller = controller
        self.clock = clock
        self.logger = logger
        self.active_high = bool(active_high)
        self.debounce_s = max(0.02, min(0.2, debounce_ms / 1000.0))
        self.request_prefix = request_prefix
        self._sequence = 0
        self._pending_start = None

    def _pressed(self):
        value = 1 if self.pin.value() else 0
        return bool(value) if self.active_high else not bool(value)

    def _min_off_remaining(self, now):
        cfg = getattr(self.controller, "irrigation_config", {}) or {}
        min_off = float(cfg.get("min_off_s", 5))
        last_stop = getattr(self.controller, "last_stop_ts", None)
        if last_stop is None:
            return 0.0
        return max(0.0, min_off - (now - last_stop))

    def _queue_start(self, delay_s, now):
        if self._pending_start is not None and not self._pending_start.done():
            return
        self.logger.info("button start queued for %.1fs (min_off)", delay_s)
        self._pending_start = asyncio.create_task(self._delayed_start(delay_s))

    async def _delayed_start(self, delay_s):
        await asyncio.sleep(delay_s)
        self._pending_start = None
        if not self.controller.relay.on:
            self.trigger()

    def trigger(self):
        now = self.clock.now()
        self._sequence += 1
        request_id = "%s-%d-%d" % (self.request_prefix, now, self._sequence)
        if self.controller.relay.on:
            result = self.controller.request("stop", "button", request_id, now)
            action = "stop"
        else:
            result = self.controller.request("start", "button", request_id, now)
            action = "start"
            if not result.get("ok") and result.get("code") == "MIN_OFF":
                self._queue_start(self._min_off_remaining(now), now)
                return True
        if not result.get("ok"):
            self.logger.info(
                "button %s rejected: %s %s",
                action,
                result.get("code"),
                result.get("message"),
            )
            return False
        self.logger.info("button %s request=%s", action, request_id)
        return True

    async def run(self):
        last = self._pressed()
        while True:
            await asyncio.sleep(self.debounce_s)
            current = self._pressed()
            if current and not last:
                # Confirm after one debounce interval and toggle only on the
                # rising edge; holding the button does not repeat.
                await asyncio.sleep(self.debounce_s)
                if self._pressed():
                    self.trigger()
            last = current
