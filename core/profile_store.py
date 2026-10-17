"""
profile_store.py
-----------------
Manages named, persistent Chrome profiles - e.g. one per client/business
account you manage - so each keeps its own cookies/logins/history across
runs, and switching between them is a name instead of remembering paths.

This stores ordinary per-profile *settings* (a proxy if that account
requires one, locale/timezone for correctly viewing region-specific content,
a free-text note on whose account it is). It does not store or apply
anything that disguises the browser's real identity (no spoofed user-agent,
canvas/WebGL noise, timezone-vs-IP mismatching, etc.) - if a target site
blocks plain automation, that's handled by slowing down or going headful,
not by masking what's making the requests.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

PROFILES_ROOT = os.path.abspath("profiles")


@dataclass
class ProfileSettings:
    name: str
    note: str = ""                    # e.g. "Acme Corp - marketing account"
    proxy: Optional[str] = None       # e.g. "http://user:pass@host:port" - only if that
                                       # account legitimately requires one (corporate VPN,
                                       # region-locked client tool, etc.)
    locale: Optional[str] = None      # e.g. "en-GB" - for correctly viewing localized content
    timezone: Optional[str] = None    # e.g. "Africa/Nairobi" - matches the account's real tz
    window_size: str = "1366,900"
    headless: bool = False


class ProfileStore:
    def __init__(self, root: str = PROFILES_ROOT):
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def _meta_path(self, name: str) -> str:
        return os.path.join(self.root, f"{name}.json")

    def _chrome_dir(self, name: str) -> str:
        path = os.path.join(self.root, name, "chrome-data")
        os.makedirs(path, exist_ok=True)
        return path

    def exists(self, name: str) -> bool:
        return os.path.exists(self._meta_path(name))

    def create(self, name: str, **kwargs) -> ProfileSettings:
        if self.exists(name):
            raise ValueError(f"Profile '{name}' already exists.")
        settings = ProfileSettings(name=name, **kwargs)
        self._save(settings)
        self._chrome_dir(name)  # ensure the Chrome data dir exists too
        return settings

    def get(self, name: str) -> ProfileSettings:
        if not self.exists(name):
            # Auto-create a bare profile on first use, so a config file can
            # just name a profile and have it come into existence.
            return self.create(name)
        with open(self._meta_path(name), "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProfileSettings(**data)

    def update(self, name: str, **kwargs) -> ProfileSettings:
        settings = self.get(name)
        for k, v in kwargs.items():
            if v is not None and hasattr(settings, k):
                setattr(settings, k, v)
        self._save(settings)
        return settings

    def _save(self, settings: ProfileSettings):
        with open(self._meta_path(settings.name), "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, indent=2)

    def list(self):
        names = sorted(
            fn[:-5] for fn in os.listdir(self.root)
            if fn.endswith(".json")
        )
        return [self.get(n) for n in names]

    def delete(self, name: str):
        import shutil
        meta = self._meta_path(name)
        if os.path.exists(meta):
            os.remove(meta)
        chrome_dir = os.path.join(self.root, name)
        if os.path.isdir(chrome_dir):
            shutil.rmtree(chrome_dir)

    def chrome_user_data_dir(self, name: str) -> str:
        return self._chrome_dir(name)
