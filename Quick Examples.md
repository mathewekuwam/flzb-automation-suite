# Quick CLI Reference & Usage Cheat Sheet

This document contains commonly used commands and quick workflows for the **FLZB Automation Suite**.

---

## 1. Dry Run / Queue Inspection (No Browser Launch)

Preview record resolution, tempmail email creation, and data validation without launching the browser:

```powershell
# Preview the next 5 records from the default queue
python signup-bot.py --limit 5 --dry-run

# Preview a single record from the latest log
python signup-bot.py --from-log latest --record-index 0 --dry-run

# Preview custom user parameters
python signup-bot.py --first "John" --last "Doe" --dry-run
```

---

## 2. Running Signup Bot (`signup-bot.py`)

### Single Record Mode
```powershell
# Run using record index 3 from latest scraped log
python signup-bot.py --from-log latest --record-index 3

# Run from a specific log file
python signup-bot.py --from-log "logs/sample_results.json" --record-index 0

# Run with explicit parameters
python signup-bot.py --first "John" --last "Doe" --dob-month 01 --dob-day 15 --dob-year 1992 --ssn "000-00-0000" --address "123 Main St" --city "Phoenix" --state "AZ" --zip "85001"
```

### Batch Mode & Range Execution
```powershell
# Process next 5 records consecutively with 5s delay
python signup-bot.py --limit 5

# Process records 10 through 20, skipping already registered records
python signup-bot.py --range 10..20 --skip-completed

# Process all records from a specific log file with a 10s cooldown
python signup-bot.py --from-log "logs/sample_results.json" --all --delay-between 10

# Retry previously failed records within index range 16 to 20
python signup-bot.py --range 16..20 --skip-completed --retry-failed --delay-between 25
```

### Headless & Profile Options
```powershell
# Run headless (background browser)
python signup-bot.py --limit 5 --headless

# Force standard local Chrome driver (bypasses MoreLogin)
python signup-bot.py --limit 5 --local

# List all available records in the selected log
python signup-bot.py --list-records
```

---

## 3. Data Scraper (`flzb-me.py` & `flzb-me-login.py`)

```powershell
# Login to flzb.me using credentials from .env or CLI
python flzb-me-login.py

# Login in headless mode
python flzb-me-login.py --headless

# Run scraper and generate TempMail inboxes for scraped records
python flzb-me.py --create-emails

# Run scraper in headless mode
python flzb-me.py --headless

# Scrape and pipe directly to signup bot for 3 accounts
python flzb-me.py --auto-signup --signup-limit 3
```

---

## 4. TempMail Client (`tempmail_client1.py`)

```powershell
# Generate a new disposable email derived from a user's name
python tempmail_client1.py --first "John" --last "Doe"

# Generate email and automatically wait/poll for the 6-digit OTP code
python tempmail_client1.py --first "John" --last "Doe" --wait-code

# Check messages for a specific email address
python tempmail_client1.py "johndoe1fc@example.com"

# Check messages by token
python tempmail_client1 "<INBOX_TOKEN>"

# List all saved local inboxes and tokens
python tempmail_client1.py --list
```

---

## 5. Startup Banner

```powershell
python banner_flzb.py
```