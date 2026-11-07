"""Validation helpers shared by the API and configuration layer."""


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_float(value, default=None):
    if is_number(value):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=None):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value, low, high):
    return low if value < low else high if value > high else value


def require_range(value, low, high, name):
    """Return (value, error).  ``value`` is a float when valid."""
    number = as_float(value)
    if number is None or number < low or number > high:
        return None, "%s must be between %s and %s" % (name, low, high)
    return number, None
