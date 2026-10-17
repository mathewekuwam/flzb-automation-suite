"""
form_fill.py
------------
Generic, reliable form-interaction helpers: type into a field and verify it
stuck, click a button, read back validation/result messages. Framework-level
utilities with no knowledge of any particular site's fields or business logic
(that lives in per-site config/bot files).
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)

from core.logging_utils import ok, warn, debug


def locator_for(selector: str):
    """
    Accepts either:
      - a CSS selector string, e.g. "#email" or "[name='email']"
      - an explicit "xpath=..." or "css=..." prefixed string
    Returns a Selenium (By, value) tuple.
    """
    if selector.startswith("xpath="):
        return (By.XPATH, selector[len("xpath="):])
    if selector.startswith("css="):
        return (By.CSS_SELECTOR, selector[len("css="):])
    return (By.CSS_SELECTOR, selector)


def type_into(driver, selector: str, value: str, wait: int = 20, retries: int = 3):
    """
    Click a field, clear it (select-all + delete, more reliable than .clear()
    on JS-framework-controlled inputs), type the value, blur it, and verify
    the value actually stuck - retrying a few times if not.
    """
    locator = locator_for(selector)
    last_seen = None
    for attempt in range(1, retries + 1):
        el = WebDriverWait(driver, wait).until(EC.element_to_be_clickable(locator))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        if el.tag_name.lower() == "select":
            from selenium.webdriver.support.ui import Select
            try:
                Select(el).select_by_value(str(value))
            except Exception:
                try:
                    Select(el).select_by_visible_text(str(value))
                except Exception:
                    el.send_keys(str(value))
        else:
            el.click()
            el.send_keys(Keys.CONTROL, "a", Keys.DELETE)
            el.send_keys(str(value))
            el.send_keys(Keys.TAB)
        time.sleep(0.3)
        last_seen = el.get_attribute("value")
        if (last_seen or "").strip() == str(value).strip():
            ok(f"Filled '{selector}'.")
            return el
        warn(f"'{selector}' shows {last_seen!r} after typing {value!r} - retrying ({attempt}/{retries}).")
        time.sleep(0.5)
    raise RuntimeError(f"Could not get '{selector}' to hold value {value!r} (last seen: {last_seen!r}).")


def field_is_invalid(driver, selector: str) -> bool:
    """
    Generic check for common 'this field failed validation' CSS hooks
    (Angular's ng-invalid, Bootstrap's is-invalid, aria-invalid). Returns
    False (i.e. "looks fine") if the field can't be found or none apply -
    we don't want a framework mismatch to block a legitimate run.
    """
    try:
        el = driver.find_element(*locator_for(selector))
    except NoSuchElementException:
        return False
    cls = (el.get_attribute("class") or "")
    aria_invalid = (el.get_attribute("aria-invalid") or "").lower() == "true"
    if aria_invalid:
        return True
    if "ng-invalid" in cls and "ng-pristine" not in cls:
        return True
    if "is-invalid" in cls:
        return True
    return False


def click(driver, selector: str, wait: int = 20):
    locator = locator_for(selector)
    btn = WebDriverWait(driver, wait).until(EC.element_to_be_clickable(locator))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    try:
        btn.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", btn)
    ok(f"Clicked '{selector}'.")


def click_by_text(driver, text: str, wait: int = 20, tag="button|input"):
    """Click a button/input whose visible text or value matches `text` exactly."""
    xpath = (
        f"//button[normalize-space()='{text}']"
        f" | //input[@type='submit' and @value='{text}']"
        f" | //a[normalize-space()='{text}']"
    )
    btn = WebDriverWait(driver, wait).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    try:
        btn.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", btn)
    ok(f"Clicked element with text '{text}'.")


def select_autocomplete_option(driver, field_selector: str, type_text: str,
                                exact_match: str = None, wait: int = 10):
    """
    Generic helper for autocomplete / typeahead dropdowns: type into the field,
    then click the first visible suggestion (or the one whose text exactly
    equals `exact_match`, if given). Works without hardcoding a site's CSS
    classes by scanning for small, visible elements positioned just below the
    input whose text contains what was typed.
    """
    field = type_into(driver, field_selector, type_text)

    find_js = """
    var typed = arguments[0].toLowerCase().replace(/\\s+/g, ' ').trim();
    var inp = arguments[1];
    var ir = inp.getBoundingClientRect();
    var skip = ['SCRIPT','STYLE','INPUT','TEXTAREA','OPTION','HEAD','META','LABEL','BUTTON'];
    var cands = [];
    document.querySelectorAll('body *').forEach(function (e) {
      if (skip.indexOf(e.tagName) >= 0 || e === inp || e.contains(inp)) return;
      var r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      var st = getComputedStyle(e);
      if (st.visibility === 'hidden' || st.display === 'none') return;
      var t = (e.innerText || '').toLowerCase().replace(/\\s+/g, ' ').trim();
      if (!t || t.length > typed.length + 150) return;
      if (t.indexOf(typed) < 0) return;
      if (r.top < ir.bottom - 8 || r.top > ir.bottom + 400) return;
      cands.push({el: e, top: r.top});
    });
    var deepest = cands.filter(function (c) {
      return !cands.some(function (o) { return o.el !== c.el && c.el.contains(o.el); });
    });
    deepest.sort(function (a, b) { return a.top - b.top; });
    return deepest.map(function (c) { return c.el; });
    """

    deadline = time.time() + wait
    chosen = None
    while time.time() < deadline and chosen is None:
        try:
            items = driver.execute_script(find_js, type_text, field)
        except WebDriverException:
            items = []
        if items:
            if exact_match:
                for item in items:
                    try:
                        if item.text.strip().lower() == exact_match.strip().lower():
                            chosen = item
                            break
                    except WebDriverException:
                        continue
            else:
                chosen = items[0]
        if chosen is None:
            time.sleep(0.2)

    if chosen is None:
        warn(f"No autocomplete suggestion found for '{type_text}' in '{field_selector}'.")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", chosen)
        chosen.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", chosen)
    ok(f"Selected autocomplete option matching '{type_text}'.")
    return True


def read_result_message(driver, selectors=None, wait_before: float = 2.0):
    """
    Look for a visible status/result message after a form submit. `selectors`
    is an optional list of CSS selectors to check, in order; sensible generic
    defaults are used if omitted.
    """
    time.sleep(wait_before)
    selectors = selectors or [
        "[role='alert']", "[role='status']",
        ".alert", ".error", ".success", ".message", ".toast", ".notification",
        "[class*='error']", "[class*='success']", "[class*='message']",
    ]
    for sel in selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
            except WebDriverException:
                continue
    return None
