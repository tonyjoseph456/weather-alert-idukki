import requests
import json
import os
import re
from html import unescape
from datetime import datetime

IMD_URL = "https://mausam.imd.gov.in/imd_latest/contents/districtwisewarnings_mc.php?id=4"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "last_alert.json"

ALERT_KEYWORDS = [
    "thunderstorm",
    "thunderstorms",
    "lightning",
    "heavy rain",
    "very heavy rain"
]


def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )


def load_state():

    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(data):

    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def extract_idukki_alert():

    html = requests.get(
        IMD_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    ).text

    pattern = re.compile(
        r'"title":\s*"([^"]+)".*?'
        r'"color":\s*"([^"]+)".*?'
        r'"info":\s*"([^"]+)"',
        re.DOTALL
    )

    for match in pattern.finditer(html):

        district = match.group(1)

        if district != "IDUKKI":
            continue

        info = unescape(match.group(3))

        issue_match = re.search(
            r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs",
            info,
            re.DOTALL
        )

        issue_time = "unknown"

        if issue_match:
            issue_time = (
                issue_match.group(1)
                + " "
                + issue_match.group(2)
            )

        return {
            "issue_time": issue_time,
            "text": info
        }

    return None


def contains_alert(text):

    text = text.lower()

    for keyword in ALERT_KEYWORDS:

        if keyword in text:
            return True

    return False


def main():

    alert = extract_idukki_alert()

    if not alert:
        return

    state = load_state()

    last_issue = state.get("last_issue")

    if (
        contains_alert(alert["text"])
        and alert["issue_time"] != last_issue
    ):

        send_telegram(
            f"""⚡ WEATHER ALERT

District: IDUKKI

Issue:
{alert["issue_time"]}

{alert["text"]}
"""
        )

        state["last_issue"] = alert["issue_time"]

    state["last_run"] = datetime.utcnow().isoformat()

    save_state(state)


if __name__ == "__main__":
    main()
