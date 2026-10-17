"""
html_form_parser.py
--------------------
Parses a page's real HTML to find its <form> elements and the fields/buttons
inside them, so a bot config's selectors and field list can be generated
from the actual markup instead of guessed and hand-typed.

Pure parsing/data functions only - no browser, no interactive prompts, no
network calls. Used by create_bot.py.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup

SKIP_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image", "file"}


@dataclass
class DetectedField:
    tag: str                    # "input" | "textarea" | "select"
    input_type: str             # e.g. "text", "email", "password", "" for textarea/select
    selector: str                # best CSS selector we could build, e.g. "#email"
    name: Optional[str] = None
    label: Optional[str] = None  # best-guess human label, for prompting the user
    placeholder: Optional[str] = None
    existing_value: Optional[str] = None
    options: Optional[List[str]] = None   # for <select>, the visible option texts
    looks_like_autocomplete: bool = False  # aria-autocomplete / role=combobox / has a <datalist>


@dataclass
class DetectedButton:
    selector: str
    text: str


@dataclass
class DetectedForm:
    index: int
    description: str            # short human-readable label to help pick between forms
    heading_text: Optional[str]  # nearby heading/title text, if any, for wait_for_text
    fields: List[DetectedField] = field(default_factory=list)
    buttons: List[DetectedButton] = field(default_factory=list)


def _best_selector(tag) -> Optional[str]:
    """Prefer #id, then [name='...'], since those are the most stable and
    are exactly what core/form_fill.py's locator_for() expects."""
    if tag.get("id"):
        return f"#{tag['id']}"
    if tag.get("name"):
        name = tag["name"].replace("'", "\\'")
        return f"[name='{name}']"
    return None


def _best_label(soup: BeautifulSoup, tag) -> Optional[str]:
    # <label for="id">
    tid = tag.get("id")
    if tid:
        label = soup.find("label", attrs={"for": tid})
        if label and label.get_text(strip=True):
            return label.get_text(strip=True)
    # wrapped in a <label>...<input>...</label>
    parent_label = tag.find_parent("label")
    if parent_label and parent_label.get_text(strip=True):
        return parent_label.get_text(strip=True)
    # fall back to placeholder / aria-label / name
    return tag.get("aria-label") or tag.get("placeholder") or tag.get("name")


def _nearby_heading_text(form_tag) -> Optional[str]:
    for sib in form_tag.find_all_previous(["h1", "h2", "h3"], limit=3):
        text = sib.get_text(strip=True)
        if text:
            return text
    return None


def find_forms(html: str) -> List[DetectedForm]:
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")

    # Some sites (Angular/React SPAs) have no <form> tag at all - the "form"
    # is just a <div> of inputs with a JS click-handler button. Fall back to
    # treating the whole document as one pseudo-form so those still work.
    containers = forms if forms else [soup]

    results = []
    for idx, container in enumerate(containers):
        detected_fields = []
        for tag in container.find_all(["input", "textarea", "select"]):
            ttype = (tag.get("type") or "text").lower() if tag.name == "input" else ""
            if tag.name == "input" and ttype in SKIP_INPUT_TYPES:
                continue
            selector = _best_selector(tag)
            if not selector:
                continue  # can't reliably target it - skip rather than guess a fragile selector

            options = None
            if tag.name == "select":
                options = [o.get_text(strip=True) for o in tag.find_all("option") if o.get_text(strip=True)]

            looks_autocomplete = (
                (tag.get("aria-autocomplete") is not None)
                or (tag.get("role") == "combobox")
                or (tag.get("list") is not None)
            )

            detected_fields.append(DetectedField(
                tag=tag.name,
                input_type=ttype,
                selector=selector,
                name=tag.get("name"),
                label=_best_label(soup, tag),
                placeholder=tag.get("placeholder"),
                existing_value=tag.get("value"),
                options=options,
                looks_like_autocomplete=looks_autocomplete,
            ))

        detected_buttons = []
        for tag in container.find_all(["button", "input"]):
            is_submit_button = tag.name == "button" and (tag.get("type") in (None, "submit", "button"))
            is_submit_input = tag.name == "input" and (tag.get("type") or "").lower() == "submit"
            if not (is_submit_button or is_submit_input):
                continue
            text = tag.get_text(strip=True) if tag.name == "button" else (tag.get("value") or "")
            selector = _best_selector(tag)
            if text or selector:
                detected_buttons.append(DetectedButton(selector=selector or "", text=text))

        heading = _nearby_heading_text(container) if forms else None
        action = container.get("action") if forms else None
        description = f"<form{f' action={action!r}' if action else ''}> with {len(detected_fields)} field(s)" \
            if forms else f"page body (no <form> tag found) with {len(detected_fields)} field(s)"

        results.append(DetectedForm(
            index=idx,
            description=description,
            heading_text=heading,
            fields=detected_fields,
            buttons=detected_buttons,
        ))

    return results
