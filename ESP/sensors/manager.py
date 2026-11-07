"""Polling and health bookkeeping for all sensors."""

from sensors.base import Reading


class SensorManager:
    def __init__(self, sensors, state, logger, stale_s=90):
        self.sensors = sensors
        self.state = state
        self.logger = logger
        self.stale_s = stale_s
        self.failures = {}
        self.readings = {}

    def poll(self, now):
        for name, sensor in self.sensors.items():
            try:
                reading = sensor.read(now)
                # SHT31 returns a pair (temperature, humidity).
                if isinstance(reading, tuple):
                    for item in reading:
                        if item is not None:
                            self._store(item_unit_name(item, name), item, now)
                else:
                    self._store(name, reading, now)
            except Exception as exc:
                self.failures[name] = self.failures.get(name, 0) + 1
                self.logger.warn("sensor %s failed: %s", name, exc)
                error = "exception: %s" % exc
                if name == "air":
                    self._store("air_temp", Reading(None, "C", False, now, error), now)
                    self._store("air_humidity", Reading(None, "%", False, now, error), now)
                else:
                    self._store(name, Reading(None, "", False, now, error), now)
        return self.readings

    def _store(self, name, reading, now):
        self.readings[name] = reading
        if reading.valid:
            self.failures[name] = 0
        else:
            self.failures[name] = self.failures.get(name, 0) + 1
        self.state.set_sensor(name, reading, now)

    def get(self, name):
        return self.readings.get(name)


def item_unit_name(reading, fallback):
    if reading.unit == "C":
        return "air_temp"
    if reading.unit == "%":
        return "air_humidity"
    return fallback
