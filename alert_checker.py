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
    "very heavy rain",
    "rain"
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

color_map = {
    "#ffff00": "🟡 YELLOW ALERT",
    "#ffa500": "🟠 ORANGE ALERT",
    "#ff0000": "🔴 RED ALERT",
    "#008000": "🟢 GREEN ALERT"
}

for match in pattern.finditer(html):

    district = match.group(1)

    if district != "IDUKKI":
        continue

    color = match.group(2).lower()

    info = unescape(match.group(3))
    info = info.replace("\\/", "/")

    issue_match = re.search(
        r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs",
        info,
        re.DOTALL
    )

    valid_match = re.search(
        r"Valid upto:\s*(\d{4})\s*Hrs",
        info,
        re.IGNORECASE
    )

    issue_time = "Unknown"
    valid_upto = "Unknown"

    if issue_match:

        dt = datetime.strptime(
            f"{issue_match.group(1)} {issue_match.group(2)}",
            "%Y-%m-%d %H%M"
        )

        issue_time = dt.strftime(
            "%d %b %Y, %I:%M %p"
        )

    if valid_match:

        dt = datetime.strptime(
            valid_match.group(1),
            "%H%M"
        )

        valid_upto = dt.strftime(
            "%I:%M %p"
        )

    message = info

    message = re.sub(
        r"<.*?>",
        "",
        message
    )

    message = re.sub(
        r"Time of issue:.*",
        "",
        message,
        flags=re.DOTALL
    )

    message = re.sub(
        r"\n\s*\n+",
        "\n\n",
        message
    ).strip()

    return {
        "issue_time": issue_match.group(1) + " " + issue_match.group(2),
        "display_issue_time": issue_time,
        "valid_upto": valid_upto,
        "alert_type": color_map.get(color, "ALERT"),
        "message": message
    }

return None



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

    last_issue = state.get("last_issue", "")
last_message = state.get("last_message", "")

message_changed = (
alert["message"].strip()
!= last_message.strip()
)

issue_changed = (
alert["issue_time"]
!= last_issue
)

if (
contains_alert(alert["message"])
and (
issue_changed
or message_changed
)
):


        send_telegram(
    f"""⚠️ IDUKKI WEATHER ALERT ⚠️

ALERT TYPE
{alert["alert_type"]}

Issue Time: {alert["display_issue_time"]}
Valid Until: {alert["valid_upto"]}

Warning Details
{alert["message"]}
"""
)


        state["last_issue"] = alert["issue_time"]
        state["last_message"] = alert["message"]


        state["last_run"] = datetime.utcnow().isoformat()

        save_state(state)


if __name__ == "__main__":
    main()
