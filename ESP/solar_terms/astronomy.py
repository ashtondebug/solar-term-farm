"""Solar-term boundaries from the Sun's apparent geocentric longitude.

The 24 terms are defined at 15-degree multiples of apparent solar longitude.
A low-precision Meeus series is accurate to well under a day (typically a few
minutes), which is sufficient for the UI target described in AGENT.md.
"""

import math

from solar_terms.data import TERM_BY_NAME, TERMS

DEG = math.pi / 180.0
J2000 = 2451545.0
UNIX_EPOCH_JD = 2440587.5
DAY = 86400


def julian_day(epoch):
    return epoch / 86400.0 + UNIX_EPOCH_JD


def solar_apparent_longitude(epoch):
    jd = julian_day(epoch)
    t = (jd - J2000) / 36525.0
    mean_longitude = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    mean_anomaly = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    m = mean_anomaly * DEG
    center = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m)
        + 0.000289 * math.sin(3 * m)
    )
    true_longitude = mean_longitude + center
    omega = (125.04 - 1934.136 * t) * DEG
    apparent = true_longitude - 0.00569 - 0.00478 * math.sin(omega)
    return apparent % 360.0


def term_index(epoch):
    longitude = solar_apparent_longitude(epoch)
    return int(((longitude - 315.0) % 360.0) / 15.0)


def _target_for(index):
    return (315.0 + 15.0 * (index % 24)) % 360.0


def _delta(epoch, target):
    return (solar_apparent_longitude(epoch) - target) % 360.0


def boundary_after(epoch, target):
    """Return the first instant at/after ``epoch`` when longitude == target.

    ``epoch`` must be before the crossing; the algorithm steps forward until
    the wrapped delta is small, then bisects.  Used by tests and the term-end
    calculation.
    """
    hi = int(epoch)
    for _ in range(40):
        if _delta(hi, target) <= 180.0:
            break
        hi += DAY
    lo = hi - DAY
    for _ in range(40):
        mid = (lo + hi) // 2
        if _delta(mid, target) > 180.0:
            lo = mid
        else:
            hi = mid
    return hi


def term_start_ts(epoch):
    index = term_index(epoch)
    target = _target_for(index)
    lo = int(epoch) - 20 * DAY
    hi = int(epoch) + DAY
    # Walk back to a point before the target crossing, then bisect.
    probe = int(epoch)
    for _ in range(40):
        if _delta(probe, target) > 180.0:
            break
        probe -= DAY
    lo = probe
    for _ in range(40):
        mid = (lo + hi) // 2
        if _delta(mid, target) > 180.0:
            lo = mid
        else:
            hi = mid
    return hi


def term_end_ts(epoch):
    index = term_index(epoch)
    target = _target_for(index + 1)
    start = term_start_ts(epoch)
    return boundary_after(start + DAY, target)


def current_term(epoch):
    index = term_index(epoch)
    data = TERMS[index % 24]
    start = term_start_ts(epoch)
    end = term_end_ts(epoch)
    return {
        "name": data["name"],
        "index": index,
        "season": data["season"],
        "angle": data["angle"],
        "date_hint": data["date_hint"],
        "intro": data["intro"],
        "proverbs": data.get("proverbs", []),
        "customs": data.get("customs", []),
        "tips": data.get("tips", []),
        "available": data["available"],
        "longitude": round(solar_apparent_longitude(epoch), 4),
        "start_ts": start,
        "end_ts": end,
        "ts": int(epoch),
    }


def term_payload(name, epoch):
    data = TERM_BY_NAME.get(name)
    if data is None:
        return None
    index = TERMS.index(data)
    payload = dict(data)
    payload["index"] = index
    payload["longitude"] = round(solar_apparent_longitude(epoch), 4)
    payload["is_current"] = data["name"] == current_term(epoch)["name"]
    return payload


def all_payloads(epoch):
    current_name = current_term(epoch)["name"]
    try:
        from solar_terms.culture import CULTURE
    except ImportError:
        CULTURE = {}
    for index, data in enumerate(TERMS):
        # Reuse the loaded term dictionaries instead of copying every
        # proverb/custom/tip; the full 24-term payload is memory-sensitive.
        content = CULTURE.get(data["name"], {})
        data.update(content)
        data["index"] = index
        data["is_current"] = data["name"] == current_name
    return TERMS
