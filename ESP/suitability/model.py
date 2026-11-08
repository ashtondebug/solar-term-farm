"""Weighted interval scoring with a hard cap for severe anomalies.

The result is deliberately *not* an arithmetic mean of the four metrics: a
severely out-of-range temperature cannot be cancelled by three perfect
readings, and invalid/stale data yields ``score=None`` instead of a fake
"normal" score.
"""

from core.validation import clamp
from sensors.base import is_stale

METRICS = ("soil", "temp", "humidity", "light")


def score_metric(value, low, high):
    """100 inside [low, high], linearly down to 0 one band-width outside."""
    if value is None:
        return 0.0
    if low <= value <= high:
        return 100.0
    span = max(high - low, 1.0)
    if value < low:
        return clamp(100.0 - 100.0 * (low - value) / span, 0.0, 100.0)
    return clamp(100.0 - 100.0 * (value - high) / span, 0.0, 100.0)


def _status(score):
    if score is None:
        return "unavailable"
    if score >= 80:
        return "good"
    if score >= 60:
        return "fair"
    if score >= 40:
        return "poor"
    return "bad"


def evaluate(readings, profile, now, stale_s=90):
    """Evaluate a sensor snapshot.

    ``readings`` maps ``soil``/``air_temp``/``air_humidity``/``light`` to
    Reading objects.  Missing, invalid or stale entries produce an
    ``unavailable`` result with explicit reasons.
    """
    values = {
        "soil": readings.get("soil"),
        "temp": readings.get("air_temp"),
        "humidity": readings.get("air_humidity"),
        "light": readings.get("light"),
    }
    reasons = []
    for key, reading in values.items():
        if reading is None:
            reasons.append("%s: missing" % key)
        elif not reading.valid:
            reasons.append("%s: %s" % (key, reading.error or "invalid"))
        elif is_stale(reading, now, stale_s):
            reasons.append("%s: stale" % key)
    if reasons:
        return {
            "score": None,
            "status": "unavailable",
            "components": {},
            "reasons": reasons,
            "profile": profile.get("key", "general"),
            "profile_name": profile.get("name", ""),
            "stage": profile.get("stage", "growth"),
            "stage_name": profile.get("stage_name", ""),
            "weights": profile.get("weights", {}),
            "ranges": profile.get("ranges", {}),
            "traits": profile.get("traits", {}),
            "stage_info": profile.get("stage_info", {}),
            "ts": int(now),
        }

    ranges = profile.get("ranges", {})
    weights = profile.get("weights", {})
    components = {}
    weighted = 0.0
    total_weight = 0.0
    for key in METRICS:
        band = ranges.get(key, [0.0, 100.0])
        component = score_metric(values[key].value, band[0], band[1])
        components[key] = int(round(component))
        weight = float(weights.get(key, 0.25))
        weighted += component * weight
        total_weight += weight

    score = weighted / total_weight if total_weight else 0.0
    # A single severe metric caps the total; it cannot be fully averaged away.
    if any(value < 30 for value in components.values()):
        score = min(score, 45.0)
    score_int = int(round(clamp(score, 0.0, 100.0)))
    return {
        "score": score_int,
        "status": _status(score_int),
        "components": components,
        "reasons": [],
        "profile": profile.get("key", "general"),
        "profile_name": profile.get("name", ""),
        "stage": profile.get("stage", "growth"),
        "stage_name": profile.get("stage_name", ""),
        "weights": profile.get("weights", {}),
        "ranges": ranges,
        "traits": profile.get("traits", {}),
        "stage_info": profile.get("stage_info", {}),
        "ts": int(now),
    }
