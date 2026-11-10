"""Formatting helpers for the TFT dashboard (host-testable)."""


def format_value(value, digits=1):
    if value is None:
        return "--"
    try:
        return ("%." + str(digits) + "f") % float(value)
    except Exception:
        return "--"


def clock_text(snapshot):
    local = (snapshot.get("device") or {}).get("now_local") or ""
    return local[11:16] if len(local) >= 16 else "--:--"
