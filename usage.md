# FLZB Automation Suite — Operational & Architecture Guide

This manual covers the system design, core modules, operational pipelines, and error handling mechanics of the **FLZB Automation Suite**.

---

## 1. System Architecture

The suite connects search/query scraping, disposable email provisioning, real-time OTP polling, and multi-step browser onboarding into an automated pipeline:

```
┌─────────────────┐       ┌───────────────────────┐
│   flzb-me.py    │ ───>  │  logs/flzb-me/        │
│ (Scrapes Leads) │       │  (JSON records)       │
└─────────────────┘       └───────────┬───────────┘
                                      │
                                      ▼
┌───────────────────────┐      ┌─────────────────────────┐
│  tempmail_client1.py  │ <──> │      signup-bot.py      │
│  (TempMail.lol API)   │      │   (Multi-Step Engine)   │
│  • Creates Name Email │      │   • Form Filling        │
│  • Polls 6-Digit OTP  │      │   • Error Circuit Break │
└───────────────────────┘      └───────────┬─────────────┘
                                           │
                                           ▼
                                ┌────────────────────────┐
                                │ AutoSignup/results.json│
                                │ (Saved Accounts / Logs)│
                                └────────────────────────┘
```

---

## 2. Core Modules Breakdown

### 2.1 Lead Scraping & Query Iterator (`flzb-me.py` & `flzb-me-login.py`)
- **Automated Authentication**: Logs in to target site, handling session cookies and authentication tokens.
- **State & Year Grid Search**: Iterates through all 50 US states (`AL` to `WY`) and birth years (`1980` to `2004`).
- **Resilient Pagination**: Continuously detects and activates the `#load_next_button` / `Load More` elements until the entire result set is fully loaded in the DOM.
- **Extraction & Normalization**: Converts table rows into structured JSON containing names, addresses, phone numbers, and dates of birth.
- **Integrated Email Attachment**: When invoked with `--create-emails`, dynamically attaches disposable email addresses created via `tempmail_client1.py`.

### 2.2 TempMail & Verification Code Engine (`tempmail_client1.py`)
- **Name-Derived Addresses**: Cleans and concatenates user names (`First` + `Last`) into alphanumeric email prefixes (e.g. `johndoe...@[domain]`).
- **Persistent Inbox Store**: Stores email-to-token mappings in `inboxes.json` for lookup and recovery across multiple script executions.
- **Multi-Strategy OTP Parser**:
  1. Priority 1: Keyword-bounded regex (`code is: (\d{6})`, `verification code: (\d{6})`).
  2. Priority 2: HTML tag enclosed numbers (`<strong>(\d{6})</strong>`, `<span>(\d{6})</span>`).
  3. Priority 3: Standalone 6-digit fallback pattern.
- **Non-blocking Polling**: Configurable polling intervals (`default: 3s`) and timeouts (`default: 120s`).

### 2.3 End-to-End Onboarding Robot (`signup-bot.py`)
- **Form Navigation**: Automates multi-step registration forms with element readiness checks and dynamic delays.
- **Two-Step Verification**: Fills the email field, waits for the verification modal, fetches the OTP from TempMail, enters the code, and clicks continue.
- **Circuit Breaker**: Detects repetitive account creation errors or anti-bot throttling, halts consecutive failed runs, and restarts browser profiles to reset session states.
- **Duplicate Prevention**: `--skip-completed` checks previous successful entries in `AutoSignup/results.json` to prevent re-processing identical records.
- **Dry Run Capability**: Resolves records and emails without starting browser instances.

### 2.4 Browser Abstraction Layer (`core/`)
- **`driver_manager.py`**: Standardized Selenium Chrome setup with support for headless mode, custom user agents, proxies, and window resolutions.
- **`profile_store.py`**: Isolated Chrome user data profiles for session persistence without cookie collision.
- **`form_fill.py`**: Low-level interaction utilities (blur triggers, JS value setting, autocomplete selectors, and validation error detection).
- **`logging_utils.py`**: Color-coded console timestamps (`[OK]`, `[WARN]`, `[ERROR]`, `[DEBUG]`).

---

## 3. Operational Workflows

### Pipeline A: Scrape Leads and Batch Onboard
1. Run query scraper for targeted state and year:
   ```powershell
   python flzb-me.py --create-emails
   ```
2. Inspect parsed records from the generated log:
   ```powershell
   python signup-bot.py --from-log latest --list-records
   ```
3. Run dry run to verify queue:
   ```powershell
   python signup-bot.py --from-log latest --limit 10 --skip-completed --dry-run
   ```
4. Execute batch registration with 10s cooldown:
   ```powershell
   python signup-bot.py --from-log latest --limit 10 --skip-completed --delay-between 10
   ```

### Pipeline B: Single Record Manual Processing
When a specific profile or record requires isolated verification:
```powershell
python signup-bot.py --first "Jane" --last "Smith" --dob-month 05 --dob-day 12 --dob-year 1991 --ssn "000-00-0000" --address "456 Elm St" --city "Dallas" --state "TX" --zip "75001"
```

---

## 4. Resilience & Error Recovery

| Error / Challenge | Recovery Behavior |
| :--- | :--- |
| **Verification code delay** | Automatically polls inbox every 3 seconds for up to 120s with visual countdown. |
| **Popup modal not opening** | Retries click action using JavaScript fallback (`arguments[0].click()`). |
| **Throttling / IP block** | Circuit breaker triggers after N consecutive errors (`--max-consecutive-errors 2`). |
| **Profile lock / crash** | `restart_browser_session()` kills previous instance and respawns a clean profile. |
| **Interrupted batch** | Restart with `--skip-completed`; previously successful records in `AutoSignup/results.json` are skipped. |

---

## 5. Security & Data Protection Checklist

- Never commit `.env` or files containing live credentials.
- Ensure `logs/`, `AutoSignup/results.json`, and `inboxes.json` remain in `.gitignore`.
- Run scripts only on environments and accounts you are authorized to automate.
