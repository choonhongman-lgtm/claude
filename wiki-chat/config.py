import json
from pathlib import Path


class Config:
    CONFIG_DIR = Path.home() / ".wiki-chat"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CACHE_FILE = CONFIG_DIR / "wiki_cache.json"

    DEFAULT = {
        "wiki_url": "",    # 예: https://nhn.dooray.com
        "wiki_token": "",  # 두레이 API 토큰
        "claude_api_key": "",
    }

    def __init__(self):
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self):
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**self.DEFAULT, **data}
        return self.DEFAULT.copy()

    def save(self):
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def is_configured(self):
        return bool(
            self._data.get("wiki_url")
            and self._data.get("wiki_token")
            and self._data.get("claude_api_key")
        )
