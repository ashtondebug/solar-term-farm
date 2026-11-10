"""Load, validate and persist the device configuration."""

from config import ConfigError, deep_merge, default_config, ensure_pin, migrate_config, public_config, validate_config


class ConfigStore:
    def __init__(self, kv, logger):
        self.kv = kv
        self.logger = logger
        self.config = None

    def load(self):
        raw = self.kv.read_json("config.json", None)
        if not isinstance(raw, dict):
            self.config = default_config()
            self._maybe_pin()
            self.save(self.config)
            self.logger.info("config: created defaults")
            return self.config

        merged = deep_merge(default_config(), raw)
        migrated = migrate_config(merged)
        errors = validate_config(merged)
        if errors:
            self.logger.error("config invalid: %s", "; ".join(errors))
            self.kv.backup("config.json")
            self.config = default_config()
            self._maybe_pin()
            self.save(self.config)
            return self.config

        self.config = merged
        if migrated or self._maybe_pin():
            self.save(self.config)
        return self.config

    def _maybe_pin(self):
        security = self.config.get("security", {})
        if security.get("require_pin") and not security.get("pin"):
            ensure_pin(self.config)
            return True
        return False

    def save(self, config):
        errors = validate_config(config)
        if errors:
            raise ConfigError("; ".join(errors))
        self.kv.write_json("config.json", config)
        self.config = config

    def get(self):
        if self.config is None:
            return self.load()
        return self.config

    def public(self):
        return public_config(self.get())
