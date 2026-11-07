"""Built-in plant profiles.

Profiles are intentionally data-only so a future settings UI or MCP tool can
add profiles without touching the scoring algorithm.  Ranges are inclusive
comfort bands; the model decays linearly outside them and caps the total when
one metric is severely out of range.
"""

GENERAL = {
    "name": "通用",
    "ranges": {
        "soil": [40.0, 70.0],
        "temp": [18.0, 28.0],
        "humidity": [50.0, 80.0],
        "light": [8000.0, 30000.0],
    },
    "weights": {
        "soil": 0.35,
        "temp": 0.25,
        "humidity": 0.15,
        "light": 0.25,
    },
}

PROFILES = {
    "general": GENERAL,
    "lettuce": {
        "name": "生菜",
        "ranges": {
            "soil": [55.0, 75.0],
            "temp": [15.0, 22.0],
            "humidity": [60.0, 85.0],
            "light": [6000.0, 20000.0],
        },
        "weights": {"soil": 0.40, "temp": 0.25, "humidity": 0.15, "light": 0.20},
    },
    "tomato": {
        "name": "番茄",
        "ranges": {
            "soil": [45.0, 70.0],
            "temp": [20.0, 30.0],
            "humidity": [50.0, 75.0],
            "light": [15000.0, 50000.0],
        },
        "weights": {"soil": 0.35, "temp": 0.30, "humidity": 0.10, "light": 0.25},
    },
    "strawberry": {
        "name": "草莓",
        "ranges": {
            "soil": [50.0, 70.0],
            "temp": [15.0, 25.0],
            "humidity": [55.0, 80.0],
            "light": [10000.0, 35000.0],
        },
        "weights": {"soil": 0.35, "temp": 0.25, "humidity": 0.15, "light": 0.25},
    },
}


def get_profile(key):
    return PROFILES.get(key or "general", GENERAL)


def profile_names():
    return [{"key": key, "name": value["name"]} for key, value in PROFILES.items()]
