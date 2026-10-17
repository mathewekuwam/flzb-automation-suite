"""
driver_manager.py
------------------
Starts and manages plain, standard Selenium Chrome sessions against a named,
persistent profile (see profile_store.py), so switching between several
real accounts/clients is just a name - each keeps its own cookies/logins/
history across runs, isolated from the others.

No anti-detect / fingerprint-spoofing layer. If a target site blocks normal
automated browsers, that's a signal to slow down, add waits, or run headful -
not to disguise the browser's identity. This framework is for sites you own
or have explicit permission to automate (QA testing, monitoring, scraping
your own or public data within that site's terms of use).
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from core.profile_store import ProfileStore, ProfileSettings


class DriverManager:
    def __init__(self, profile_name: str, store: ProfileStore = None,
                 headless: bool = None, window_size: str = None):
        """
        profile_name: a name from `python manage_profiles.py list`, or a new
                      one to create it on first use.
        headless / window_size: override that profile's saved settings for
                      just this run, if given.
        """
        self.store = store or ProfileStore()
        self.settings: ProfileSettings = self.store.get(profile_name)
        if headless is not None:
            self.settings.headless = headless
        if window_size is not None:
            self.settings.window_size = window_size
        self.driver = None

    def start(self):
        options = Options()
        user_data_dir = self.store.chrome_user_data_dir(self.settings.name)
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--window-size={self.settings.window_size}")
        if self.settings.headless:
            options.add_argument("--headless=new")
        if self.settings.locale:
            options.add_argument(f"--lang={self.settings.locale}")
        if self.settings.proxy:
            options.add_argument(f"--proxy-server={self.settings.proxy}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        # Standard, undisguised automation. No navigator.webdriver patching,
        # no UA spoofing, no proxy-rotation hooks, no canvas/WebGL noise.

        service = Service()  # Selenium Manager resolves the right chromedriver
        self.driver = webdriver.Chrome(service=service, options=options)

        if self.settings.timezone:
            try:
                self.driver.execute_cdp_cmd(
                    "Emulation.setTimezoneOverride",
                    {"timezoneId": self.settings.timezone},
                )
            except Exception:
                pass  # non-fatal: just a display nicety for the account's real tz

        return self.driver

    def stop(self):
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, tb):
        self.stop()
