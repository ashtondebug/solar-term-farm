"""Persist imported plant profiles in /data/plants.json."""

from suitability.plants import normalize_import, register_profiles


class PlantProfileStore:
    def __init__(self, kv, logger=None):
        self.kv = kv
        self.logger = logger
        self.profiles = []

    def load(self):
        payload = self.kv.read_json("plants.json", None)
        if not isinstance(payload, dict):
            self.profiles = []
            return self.profiles
        try:
            profiles = normalize_import(payload)
        except ValueError as exc:
            if self.logger:
                self.logger.warn("plants.json invalid: %s", exc)
            self.profiles = []
            return self.profiles
        register_profiles(profiles)
        self.profiles = profiles
        if self.logger:
            self.logger.info("loaded %d imported plant profiles", len(profiles))
        return profiles

    def save(self, profiles):
        payload = {"version": 1, "plants": profiles}
        self.kv.write_json("plants.json", payload)
        register_profiles(profiles)
        self.profiles = profiles
