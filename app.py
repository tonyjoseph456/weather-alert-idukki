from flask import Flask
import os
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# -------------------------
# CONFIG
# -------------------------

TASK_ID = "AWmSRzWej5d5EXGLD"

# -------------------------
# APIFY HELPERS
# -------------------------

def get_apify_token():
    token = os.getenv("APIFY_TOKEN")

    if not token:
        raise Exception("APIFY_TOKEN not configured")

    return token


def get_latest_dataset_id():

    token = get_apify_token()

    url = (
        f"https://api.apify.com/v2/actor-tasks/"
        f"{TASK_ID}/runs/last"
        f"?token={token}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    return data["data"]["defaultDatasetId"]


def get_posts(limit=100):

    token = get_apify_token()

    dataset_id = get_latest_dataset_id()

    url = (
        f"https://api.apify.com/v2/datasets/"
        f"{dataset_id}/items"
        f"?token={token}"
        f"&clean=true"
        f"&desc=true"
        f"&limit={limit}"
    )

    response = requests.get(url)
    response.raise_for_status()

    posts = response.json()

    posts.sort(
        key=lambda x: x.get("time", ""),
        reverse=True
    )

    return posts


# -------------------------
# NOWCAST HELPERS
# -------------------------

def is_nowcast(post):

    text = post.get("text", "")

    return "NOWCAST" in text.upper()


def contains_idukki(post):

    text = post.get("text", "").lower()

    return (
        "idukki" in text or
        "ഇടുക്കി" in text
    )


def convert_fb_time_to_ist(fb_time):

    try:

        dt = datetime.fromisoformat(
            fb_time.replace("Z", "+00:00")
        )

        ist = dt.astimezone(
            ZoneInfo("Asia/Kolkata")
        )

        return ist.strftime(
            "%d/%m/%Y %I:%M:%S %p IST"
        )

    except:
        return fb_time


def extract_issue_datetime(text):

    issue_date = "Unknown"
    issue_time = "Unknown"

    date_match = re.search(
        r"NOWCAST dated\s+(\d{2}/\d{2}/\d{4})",
        text,
        re.IGNORECASE
    )

    if date_match:
        issue_date = date_match.group(1)

    time_match = re.search(
        r"Time of issue\s+([0-9]{3,4})\s*hr",
        text,
        re.IGNORECASE
    )

    if time_match:

        raw = time_match.group(1).zfill(4)

        hour = raw[:2]
        minute = raw[2:]

        issue_time = f"{hour}:{minute}"

    return issue_date, issue_time


def get_last_5_idukki_nowcasts():

    posts = get_posts(100)

    results = []

    for post in posts:

        if not is_nowcast(post):
            continue

        if not contains_idukki(post):
            continue

        issue_date, issue_time = extract_issue_datetime(
            post.get("text", "")
        )

        results.append({

            "fb_post_datetime":
                convert_fb_time_to_ist(
                    post.get("time")
                ),

            "issue_date":
                issue_date,

            "issue_time":
                issue_time,

            "url":
                post.get("url"),

            "text":
                post.get("text", "")
        })

        if len(results) >= 5:
            break

    return results


# -------------------------
# ROUTES
# -------------------------

@app.route("/")
def home():

    return """
    <h2>Weather Alert Service Running</h2>

    <p>
        <a href="/last5">
            Last 5 NOWCAST Posts
        </a>
    </p>

    <p>
        <a href="/debug">
            Debug Posts
        </a>
    </p>

    <p>
        <a href="/dataset">
            Current Dataset
        </a>
    </p>
    """


@app.route("/dataset")
def dataset():

    return {
        "dataset_id": get_latest_dataset_id()
    }


@app.route("/debug")
def debug():

    posts = get_posts(20)

    html = """
    <html>
    <body>
    <h2>Latest Dataset Posts</h2>
    """

    for post in posts:

        html += f"""
        <hr>

        <b>FB Time:</b>
        {post.get("time")}
        <br><br>

        <pre>
{post.get("text","")[:1200]}
        </pre>
        """

    html += "</body></html>"

    return html


@app.route("/last5")
def last5():

    posts = get_last_5_idukki_nowcasts()

    html = """
    <!DOCTYPE html>
    <html>
    <head>

    <meta charset="utf-8">

    <title>
    Last 5 Idukki NOWCASTs
    </title>

    <style>

    body{
        font-family:Arial;
        background:#f5f5f5;
        max-width:1200px;
        margin:auto;
        padding:20px;
    }

    .card{
        background:white;
        padding:20px;
        margin-bottom:20px;
        border-radius:10px;
        box-shadow:0 2px 10px rgba(0,0,0,0.1);
    }

    h1{
        color:#1565c0;
    }

    pre{
        white-space:pre-wrap;
    }

    </style>

    </head>
    <body>

    <h1>
    Last 5 NOWCAST Posts mentioning Idukki
    </h1>
    """

    for i, post in enumerate(posts, start=1):

        html += f"""

        <div class="card">

        <h2>NOWCAST #{i}</h2>

        <p>

        <b>Date & Time Posted in FB:</b>

        <br>

        {post["fb_post_datetime"]}

        </p>

        <p>

        <b>Date of Issue:</b>

        <br>

        {post["issue_date"]}

        </p>

        <p>

        <b>Time of Issue:</b>

        <br>

        {post["issue_time"]}

        </p>

        <p>

        <b>Facebook Post URL:</b>

        <br>

        <a href="{post["url"]}" target="_blank">
            Open Post
        </a>

        </p>

        <p>

        <b>Text (Idukki present):</b>

        </p>

        <pre>
{post["text"]}
        </pre>

        </div>
        """

    html += """
    </body>
    </html>
    """

    return html


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 8080)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
