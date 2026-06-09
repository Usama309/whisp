import copy
import json

from whisp import config


class Settings:
    def __init__(self, data: dict):
        self._data = data

    @classmethod
    def load(cls) -> "Settings":
        data = copy.deepcopy(config.DEFAULT_SETTINGS)
        path = config.settings_path()
        if path.exists():
            try:
                stored = json.loads(path.read_text())
                if isinstance(stored, dict):
                    data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass
        return cls(data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)

    def save(self) -> None:
        config.settings_path().write_text(json.dumps(self._data, indent=2))
