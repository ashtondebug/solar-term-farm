"""Plant profiles, stage-specific preferences and import validation.

Built-in profiles are intentionally small and generic.  Imported profiles can
provide a range and optional weights per growth stage.  Soil temperature is
accepted as metadata because the current hardware has no soil-temperature
sensor; the scorer only uses the four measured metrics.
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

STAGES = {
    "seedling": {
        "name": "苗期",
        "multipliers": {"soil": 1.0, "temp": 1.2, "humidity": 1.1, "light": 0.9},
    },
    "growth": {
        "name": "生长期",
        "multipliers": {"soil": 1.0, "temp": 1.0, "humidity": 1.0, "light": 1.0},
    },
    "flowering": {
        "name": "开花结果期",
        "multipliers": {"soil": 1.2, "temp": 1.0, "humidity": 1.2, "light": 1.1},
    },
    "harvest": {
        "name": "成熟采收期",
        "multipliers": {"soil": 0.9, "temp": 0.8, "humidity": 1.0, "light": 1.0},
    },
}

METRICS = ("soil", "temp", "humidity", "light")
LIMITS = {
    "soil": (0.0, 100.0),
    "temp": (-50.0, 60.0),
    "humidity": (0.0, 100.0),
    "light": (0.0, 200000.0),
    "soil_temp": (-20.0, 60.0),
    "air_temp_day": (-50.0, 60.0),
    "air_temp_night": (-50.0, 60.0),
    "vpd_kpa": (0.0, 10.0),
    "dli_mol_m2_day": (0.0, 100.0),
}
ALIASES = {
    "soil": "soil",
    "soil_moisture": "soil",
    "temp": "temp",
    "air_temp": "temp",
    "humidity": "humidity",
    "air_humidity": "humidity",
    "light": "light",
    "soil_temp": "soil_temp",
    "air_temp_day": "air_temp_day",
    "air_temp_night": "air_temp_night",
    "vpd_kpa": "vpd_kpa",
    "dli_mol_m2_day": "dli_mol_m2_day",
}
ENUMS = {
    "lifecycle": ("annual", "biennial", "perennial"),
    "root_type": ("taproot", "fibrous", "adventitious"),
    "photoperiod_type": ("short_day", "long_day", "day_neutral"),
    "drought_sensitivity": ("low", "medium", "high"),
    "waterlogging_sensitivity": ("low", "medium", "high"),
    "confidence": ("low", "medium", "high"),
}
TRAIT_NUMBERS = {
    "root_depth_cm": (0.0, 1000.0),
    "mature_height_cm": (0.0, 10000.0),
    "spacing_cm": (0.0, 10000.0),
    "days_to_harvest": (0.0, 3650.0),
    "frost_tolerance_c": (-50.0, 60.0),
    "heat_stress_c": (-20.0, 80.0),
    "max_dry_down_pct": (0.0, 100.0),
    "critical_daylength_h": (0.0, 24.0),
    "gdd_base_c": (-10.0, 40.0),
}
TRAIT_STRINGS = (
    "plant_habit",
    "support",
    "pruning",
    "pollination",
    "irrigation_strategy",
    "source",
    "region",
    "cultivar",
    "harvest_window",
)
TRAIT_RANGES = {
    "vpd_kpa": (0.0, 10.0),
    "dli_mol_m2_day": (0.0, 100.0),
    "soil_ph_range": (0.0, 14.0),
    "soil_ec_range": (0.0, 20.0),
    "co2_range": (0.0, 5000.0),
}
BUILTIN_KEYS = set(PROFILES.keys())


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize_range(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be [min, max]" % name)
    low, high = value
    if not _is_number(low) or not _is_number(high):
        raise ValueError("%s must contain numbers" % name)
    low = float(low)
    high = float(high)
    if low > high:
        raise ValueError("%s min must be <= max" % name)
    limits = LIMITS.get(name)
    if limits and (low < limits[0] or high > limits[1]):
        raise ValueError("%s outside allowed range" % name)
    return [low, high]


def _normalize_weights(value, stage):
    if value is None:
        return {metric: 0.25 for metric in METRICS}
    if not isinstance(value, dict):
        raise ValueError("stages.%s.weights must be an object" % stage)
    weights = {}
    for source, target in ALIASES.items():
        if target not in METRICS:
            continue
        if source in value:
            number = value[source]
            if source == target or target not in weights:
                weights[target] = number
    for metric in METRICS:
        if metric not in weights or not _is_number(weights[metric]):
            raise ValueError("stages.%s.weights.%s must be a number" % (stage, metric))
        if weights[metric] < 0 or weights[metric] > 1:
            raise ValueError("stages.%s.weights.%s must be 0..1" % (stage, metric))
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("stages.%s.weights must have a positive total" % stage)
    return {metric: weights[metric] / total for metric in METRICS}


def _normalize_strings(value, name):
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError("%s must be an array of at most 12 strings" % name)
    result = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 120:
            raise ValueError("%s entries must be non-empty strings" % name)
        result.append(item)
    return result


def _normalize_traits(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("plant.traits must be an object")
    result = {}
    for key, allowed in ENUMS.items():
        if key in raw:
            if raw[key] not in allowed:
                raise ValueError("traits.%s must be one of: %s" % (key, ", ".join(allowed)))
            result[key] = raw[key]
    for key in TRAIT_STRINGS:
        if key in raw:
            if not isinstance(raw[key], str) or not raw[key] or len(raw[key]) > 240:
                raise ValueError("traits.%s must be a non-empty string" % key)
            result[key] = raw[key]
    for key, limits in TRAIT_NUMBERS.items():
        if key in raw:
            value = raw[key]
            if not _is_number(value) or value < limits[0] or value > limits[1]:
                raise ValueError("traits.%s outside allowed range" % key)
            result[key] = float(value)
    for key, limits in TRAIT_RANGES.items():
        if key in raw:
            result[key] = _normalize_range(raw[key], key)
            if result[key][0] < limits[0] or result[key][1] > limits[1]:
                raise ValueError("traits.%s outside allowed range" % key)
    for key in ("disease_risks", "pest_risks"):
        if key in raw:
            result[key] = _normalize_strings(raw[key], "traits.%s" % key)
    for key in ("reviewed", "control_eligible"):
        if key in raw:
            if not isinstance(raw[key], bool):
                raise ValueError("traits.%s must be a boolean" % key)
            result[key] = raw[key]
    return result


def normalize_import(payload):
    """Validate an import payload and return canonical profile dictionaries."""
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    if payload.get("version") not in (None, 1):
        raise ValueError("unsupported profile schema version")
    plants = payload.get("plants", payload.get("profiles"))
    if not isinstance(plants, list) or not plants:
        raise ValueError("plants must be a non-empty array")
    result = []
    seen = set()
    for item in plants:
        if not isinstance(item, dict):
            raise ValueError("each plant must be an object")
        key = item.get("key")
        if not isinstance(key, str) or not key or len(key) > 32:
            raise ValueError("plant.key must be a string of 1..32 characters")
        if key in BUILTIN_KEYS:
            raise ValueError("plant.key '%s' is reserved by a built-in profile" % key)
        if key in seen:
            raise ValueError("duplicate plant.key '%s'" % key)
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        if any(char not in allowed for char in key):
            raise ValueError("plant.key may contain letters, numbers, _ and -")
        name = item.get("name", key)
        if not isinstance(name, str) or not name or len(name) > 64:
            raise ValueError("plant.name must be a string of 1..64 characters")
        stages = item.get("stages")
        if not isinstance(stages, dict) or not stages:
            raise ValueError("plant.stages must be a non-empty object")
        normalized_stages = {}
        for stage_name, stage in stages.items():
            if stage_name not in STAGES:
                raise ValueError("unknown stage '%s'" % stage_name)
            if not isinstance(stage, dict):
                raise ValueError("stages.%s must be an object" % stage_name)
            ranges = stage.get("ranges")
            if not isinstance(ranges, dict):
                raise ValueError("stages.%s.ranges must be an object" % stage_name)
            normalized_ranges = {}
            for source, target in ALIASES.items():
                if source in ranges and target not in normalized_ranges:
                    normalized_ranges[target] = _normalize_range(
                        ranges[source], target
                    )
            for metric in METRICS:
                if metric not in normalized_ranges:
                    raise ValueError(
                        "stages.%s.ranges.%s is required" % (stage_name, metric)
                    )
            for extra, limits in (
                ("vpd_kpa", (0.0, 10.0)),
                ("dli_mol_m2_day", (0.0, 100.0)),
            ):
                if extra in normalized_ranges:
                    if normalized_ranges[extra][0] < limits[0] or normalized_ranges[extra][1] > limits[1]:
                        raise ValueError("stages.%s.ranges.%s outside allowed range" % (stage_name, extra))
            normalized_stages[stage_name] = {
                "ranges": normalized_ranges,
                "weights": _normalize_weights(stage.get("weights"), stage_name),
            }
            for extra in ("days_to_next_stage", "gdd_to_next_stage"):
                if extra in stage:
                    value = stage[extra]
                    if not _is_number(value) or value < 0 or value > 5000:
                        raise ValueError("stages.%s.%s outside allowed range" % (stage_name, extra))
                    normalized_stages[stage_name][extra] = float(value)
            if "advice" in stage:
                normalized_stages[stage_name]["advice"] = _normalize_strings(
                    stage["advice"], "stages.%s.advice" % stage_name
                )
        seen.add(key)
        result.append(
            {
                "key": key,
                "name": name,
                "stages": normalized_stages,
                "traits": _normalize_traits(item.get("traits")),
            }
        )
    return result


def register_profiles(profiles):
    for profile in profiles:
        PROFILES[profile["key"]] = profile


def get_profile(key, stage="growth", weights=None):
    profile = PROFILES.get(key or "general", GENERAL)
    stages = profile.get("stages")
    stage_key = stage if stage in STAGES else "growth"
    if stages:
        if stage_key not in stages:
            stage_key = "growth" if "growth" in stages else next(iter(stages))
        chosen = stages[stage_key]
        ranges = chosen.get("ranges", {})
        base_weights = chosen.get("weights", {})
        multiplier = {metric: 1.0 for metric in METRICS}
    else:
        ranges = profile.get("ranges", {})
        base_weights = profile.get("weights", {})
        multiplier = STAGES.get(stage_key, STAGES["growth"])["multipliers"]
    effective = {}
    for metric in METRICS:
        effective[metric] = float(base_weights.get(metric, 0.25)) * multiplier.get(metric, 1.0)
    if weights:
        effective = {metric: float(weights[metric]) for metric in METRICS}
    total = sum(effective.values())
    if total > 0:
        effective = {metric: value / total for metric, value in effective.items()}
    stage_info = {}
    if stages:
        for key in ("days_to_next_stage", "gdd_to_next_stage", "advice"):
            if key in chosen:
                stage_info[key] = chosen[key]
    return {
        "key": key if key in PROFILES else "general",
        "name": profile.get("name", key),
        "stage": stage_key,
        "stage_name": STAGES[stage_key]["name"],
        "ranges": ranges,
        "weights": effective,
        "traits": profile.get("traits", {}),
        "stage_info": stage_info,
    }


def profile_names():
    result = []
    for key, profile in PROFILES.items():
        stages = profile.get("stages")
        result.append(
            {
                "key": key,
                "name": profile.get("name", key),
                "builtin": key in BUILTIN_KEYS,
                "stages": list(stages.keys()) if stages else list(STAGES.keys()),
            }
        )
    return result


def stage_names():
    return [{"key": key, "name": value["name"]} for key, value in STAGES.items()]
