"""
Checks the 22K gold price for Bangalore on goodreturns.in and sends a
Telegram message ONLY when the price has changed since the last check.

State (the last known price) is stored in last_price.txt, which this
script updates each run. The GitHub Actions workflow commits that file
back to the repo so the next run remembers where things left off.
"""

import os
import re
import sys

import requests

URL = "https://www.goodreturns.in/gold-rates/bangalore.html"
STATE_FILE = "last_price.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def get_current_price() -> int:
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    text = resp.text

    # Primary pattern: "...per gram for 22 karat gold (91.6% purity)..."
    # preceded by "Rs.XX,XXX" earlier in the same sentence.
    m = re.search(r"₹\s*([\d,]+)\s*per gram for 22 karat gold", text)

    if not m:
        # Fallback: the "22K Gold /g" ticker widget near the top of the page.
        m = re.search(r"22K\s*Gold\s*/?\s*g.*?₹\s*([\d,]+)", text, re.DOTALL)

    if not m:
        raise ValueError(
            "Could not find the 22K gold price on the page — "
            "the site layout may have changed. Check the regex patterns."
        )

    return int(m.group(1).replace(",", ""))


def send_telegram(message: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(api_url, data={"chat_id": chat_id, "text": message}, timeout=20)
    r.raise_for_status()


def read_last_price():
    if not os.path.exists(STATE_FILE):
        return None
    content = open(STATE_FILE).read().strip()
    return int(content) if content else None


def write_last_price(price: int) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(str(price))


def main():
    current = get_current_price()
    last = read_last_price()

    if last is None:
        print(f"First run — recording baseline price: Rs.{current}. No alert sent.")
    elif current != last:
        diff = current - last
        direction = "up" if diff > 0 else "down"
        message = (
            f"Gold price alert (Bangalore, 22K)\n"
            f"Rs.{last} -> Rs.{current}\n"
            f"{direction} by Rs.{abs(diff)}"
        )
        print(message)
        send_telegram(message)
    else:
        print(f"No change — price still Rs.{current}.")

    write_last_price(current)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
