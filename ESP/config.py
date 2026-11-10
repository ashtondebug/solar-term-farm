"""Configuration defaults, merging and validation.

The configuration is a plain nested dict on purpose: MicroPython does not
ship dataclasses and dicts serialize directly to JSON for the API and the
on-device config file.

Security note: the Wi-Fi password and the device PIN never live in the
public config returned by the web API.  ``public_config`` is the only
function the API layer should use.
"""

import os

from suitability.plants import PROFILES as PLANT_PROFILES, STAGES as PLANT_STAGES
from version import VERSION

DEFAULT_CONFIG = {
    "device": {
        "name": "AgriVerse",
        "timezone_offset": 8 * 3600,
    },
    "sampling": {
        "interval_s": 30,
        "history_interval_s": 300,
        "history_days": 7,
    },
    "plant": {
        "profile": "general",
        "stage": "growth",
        "weights": None,
    },
    "irrigation": {
        "mode": "auto",
        "soil_threshold": 35.0,
        "hysteresis": 3.0,
        "max_run_s": 20,
        "min_interval_s": 1800,
        "min_off_s": 5,
        "sensor_stale_s": 90,
    },
    "security": {
        # PIN enforcement stays off until a local UI can display the PIN.
        "require_pin": False,
        "pin": "",
    },
    "calibration": {
        "soil_dry": None,
        "soil_wet": None,
    },
    "pins": {
        "soil_adc": 4,
        "i2c_sda": 8,
        "i2c_scl": 9,
        "tft_sck": 40,
        "tft_sda": 39,
        "tft_rst": 38,
        "tft_dc": 2,
        "tft_cs": 1,
        "button": 41,
        "relay": 5,
    },
    "features": {
        "web": True,
    },
    "tft": {
        "enabled": True,
        "rotation": 3,
        "freq": 20000000,
        "width": 240,
        "height": 320,
    },
    "button": {
        "enabled": True,
        "active_high": True,
        "debounce_ms": 50,
    },
}

VALID_MODES = ("auto", "manual")


class ConfigError(Exception):
    """Raised when a configuration document cannot be accepted."""


def _copy(value):
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def default_config():
    """Return a fresh, mutable copy of the defaults."""
    return _copy(DEFAULT_CONFIG)


def migrate_config(config):
    """Remove fields from the retired TJC/UART screen design."""
    changed = False
    if isinstance(config.get("display"), dict):
        config.pop("display", None)
        changed = True
    if isinstance(config.get("oled"), dict):
        config.pop("oled", None)
        changed = True
    features = config.get("features")
    if isinstance(features, dict) and "display" in features:
        features.pop("display", None)
        changed = True
    pins = config.get("pins")
    if isinstance(pins, dict):
        for key in ("uart_tx", "uart_rx", "oled_sda", "oled_scl"):
            if key in pins:
                pins.pop(key, None)
                changed = True
        if pins.get("button") == 14:
            pins["button"] = 41
            changed = True
    return changed


def deep_merge(base, override):
    """Recursively merge ``override`` into a copy of ``base``."""
    out = _copy(base)
    if not isinstance(override, dict):
        return out
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = _copy(value)
    return out


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def generate_pin():
    """Generate a 6-digit PIN without importing a heavy RNG on the device."""
    try:
        number = int.from_bytes(os.urandom(4), "big") % 1000000
    except Exception:
        try:
            import random

            number = random.randint(0, 999999)
        except Exception:
            number = 0
    return "%06d" % number


def validate_config(config):
    """Return a list of human-readable validation errors (empty = valid)."""
    errors = []
    if not isinstance(config, dict):
        return ["config must be an object"]

    device = config.get("device", {})
    if not isinstance(device.get("name"), str) or not device.get("name", "").strip():
        errors.append("device.name must be a non-empty string")
    offset = device.get("timezone_offset")
    if not is_number(offset) or offset < -12 * 3600 or offset > 14 * 3600:
        errors.append("device.timezone_offset must be between -43200 and 50400 seconds")

    sampling = config.get("sampling", {})
    _check_range(errors, "sampling.interval_s", sampling.get("interval_s"), 5, 3600)
    _check_range(errors, "sampling.history_interval_s", sampling.get("history_interval_s"), 60, 3600)
    _check_range(errors, "sampling.history_days", sampling.get("history_days"), 1, 30)

    plant = config.get("plant", {})
    if plant.get("profile") not in PLANT_PROFILES:
        errors.append("plant.profile must be one of: %s" % ", ".join(sorted(PLANT_PROFILES)))
    if plant.get("stage") not in PLANT_STAGES:
        errors.append("plant.stage must be one of: %s" % ", ".join(sorted(PLANT_STAGES)))
    weights = plant.get("weights")
    if weights is not None:
        if not isinstance(weights, dict):
            errors.append("plant.weights must be an object or null")
        else:
            metric_weights = []
            for metric in ("soil", "temp", "humidity", "light"):
                value = weights.get(metric)
                _check_range(errors, "plant.weights.%s" % metric, value, 0, 1)
                if is_number(value):
                    metric_weights.append(value)
            if len(metric_weights) == 4 and sum(metric_weights) <= 0:
                errors.append("plant.weights must have a positive total")

    irrigation = config.get("irrigation", {})
    if irrigation.get("mode") not in VALID_MODES:
        errors.append("irrigation.mode must be 'auto' or 'manual'")
    _check_range(errors, "irrigation.soil_threshold", irrigation.get("soil_threshold"), 0, 100)
    _check_range(errors, "irrigation.hysteresis", irrigation.get("hysteresis"), 0, 20)
    _check_range(errors, "irrigation.max_run_s", irrigation.get("max_run_s"), 1, 120)
    _check_range(errors, "irrigation.min_interval_s", irrigation.get("min_interval_s"), 0, 86400)
    _check_range(errors, "irrigation.min_off_s", irrigation.get("min_off_s"), 0, 60)
    _check_range(errors, "irrigation.sensor_stale_s", irrigation.get("sensor_stale_s"), 10, 600)

    security = config.get("security", {})
    if not isinstance(security.get("require_pin"), bool):
        errors.append("security.require_pin must be a boolean")
    pin = security.get("pin", "")
    if pin and (not isinstance(pin, str) or len(pin) != 6 or not pin.isdigit()):
        errors.append("security.pin must be empty or a 6-digit string")

    calibration = config.get("calibration", {})
    dry = calibration.get("soil_dry")
    wet = calibration.get("soil_wet")
    if (dry is None) != (wet is None):
        errors.append("calibration.soil_dry and calibration.soil_wet must both be set or both be null")
    elif dry is not None:
        _check_range(errors, "calibration.soil_dry", dry, 0, 65535)
        _check_range(errors, "calibration.soil_wet", wet, 0, 65535)
        if is_number(dry) and is_number(wet) and abs(dry - wet) < 500:
            errors.append("calibration dry/wet values are too close (need |dry-wet| >= 500)")

    pins = config.get("pins", {})
    pin_values = []
    pin_keys = (
        "soil_adc", "i2c_sda", "i2c_scl",
        "tft_sck", "tft_sda", "tft_rst", "tft_dc", "tft_cs",
        "button", "relay",
    )
    for key in pin_keys:
        value = pins.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 48:
            errors.append("pins.%s must be an integer GPIO number" % key)
        else:
            pin_values.append(value)
    if len(pin_values) == len(pin_keys) and len(set(pin_values)) != len(pin_keys):
        errors.append("pins must be unique across soil/i2c/tft/button/relay")

    features = config.get("features", {})
    if not isinstance(features.get("web"), bool):
        errors.append("features.web must be a boolean")

    tft = config.get("tft", {})
    if not isinstance(tft, dict):
        errors.append("tft must be an object")
    else:
        if not isinstance(tft.get("enabled"), bool):
            errors.append("tft.enabled must be a boolean")
        if tft.get("rotation") not in (0, 1, 2, 3):
            errors.append("tft.rotation must be 0, 1, 2 or 3")
        _check_range(errors, "tft.freq", tft.get("freq"), 1000000, 40000000)
        if tft.get("width") != 240 or tft.get("height") != 320:
            errors.append("tft.width/height must be 240x320")

    button = config.get("button", {})
    if not isinstance(button, dict):
        errors.append("button must be an object")
    else:
        if not isinstance(button.get("enabled"), bool):
            errors.append("button.enabled must be a boolean")
        if not isinstance(button.get("active_high"), bool):
            errors.append("button.active_high must be a boolean")
        _check_range(errors, "button.debounce_ms", button.get("debounce_ms"), 20, 200)

    return errors


def _check_range(errors, path, value, low, high):
    if not is_number(value) or value < low or value > high:
        errors.append("%s must be a number between %s and %s" % (path, low, high))


def ensure_valid(config):
    errors = validate_config(config)
    if errors:
        raise ConfigError("; ".join(errors))


def public_config(config):
    """Return a JSON-safe config with secrets removed."""
    out = _copy(config)
    security = out.get("security", {})
    security.pop("pin", None)
    security["pin_required"] = bool(security.get("require_pin"))
    out["security"] = security
    out.pop("wifi", None)
    return out


def ensure_pin(config):
    """Generate and persist a PIN in-place when the field is empty."""
    security = config.setdefault("security", {})
    if not security.get("pin"):
        security["pin"] = generate_pin()
    return security["pin"]


def version_string():
    return "%s %s" % (VERSION, BUILD_STAGE)
