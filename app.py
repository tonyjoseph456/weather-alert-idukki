from flask import Flask
import os
import requests
import json
import re

app = Flask(__name__)

# Your Apify Dataset ID
DATASET_ID = "NYyRqc7fTqJQwsvDJ"


def get_posts(limit=100):
    token = os.getenv("APIFY_TOKEN")

    if not token:
        raise Exception("APIFY_TOKEN environment variable not configured")

    url = (
        f"https://api.apify.com/v2/datasets/"
        f"{DATASET_ID}/items"
        f"?token={token}"
        f"&clean=true"
        f"&limit={limit}"
    )

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def is_nowcast(post):
    text = post.get("text", "")
    return "NOWCAST" in text.upper()


def contains_idukki(post):
    text = post.get("text", "").lower()

    return (
        "idukki" in text or
        "ഇടുക്കി" in text
    )


def extract_issue_datetime(text):

    issue_date = "Unknown"
    issue_time = "Unknown"

    # English section
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
        issue_time = time_match.group(1)

    # Malayalam fallback
    if issue_date == "Unknown":

        mal_date = re.search(
            r"പുറപ്പെടുവിച്ച സമയവും തീയതിയും.*?(\d{2}/\d{2}/\d{4})",
            text
        )

        if mal_date:
            issue_date = mal_date.group(1)

    if issue_time == "Unknown":

        mal_time = re.search(
            r"പുറപ്പെടുവിച്ച സമയവും തീയതിയും\s*([0-9.: ]+(?:AM|PM))",
            text,
            re.IGNORECASE
        )

        if mal_time:
            issue_time = mal_time.group(1)

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
            "fb_post_datetime": post.get("time"),
            "issue_date": issue_date,
            "issue_time": issue_time,
            "text": post.get("text", "")
        })

        if len(results) >= 5:
            break

    return results


@app.route("/")
def home():
    return """
    <h2>Weather Alert Service Running</h2>

    <p>
        <a href="/check">Latest NOWCAST JSON</a>
    </p>

    <p>
        <a href="/last5">Last 5 Idukki NOWCASTs</a>
    </p>
    """


@app.route("/check")
def check():

    try:

        posts = get_last_5_idukki_nowcasts()

        if not posts:
            return {
                "status": "no_idukki_nowcast_found"
            }

        latest = posts[0]

        return app.response_class(
            response=json.dumps(
                latest,
                ensure_ascii=False,
                indent=2
            ),
            mimetype="application/json"
        )

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


@app.route("/last5")
def last5():

    try:

        posts = get_last_5_idukki_nowcasts()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Idukki NOWCAST Alerts</title>

            <style>

                body {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: auto;
                    padding: 20px;
                    background: #f5f5f5;
                }

                h1 {
                    text-align: center;
                    color: #333;
                }

                .card {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }

                .title {
                    font-size: 22px;
                    font-weight: bold;
                    color: #d32f2f;
                    margin-bottom: 15px;
                }

                .label {
                    font-weight: bold;
                    color: #1565c0;
                }

                .text {
                    white-space: pre-wrap;
                    background: #fafafa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-top: 15px;
                    line-height: 1.6;
                }

            </style>

        </head>
        <body>

            <h1>🌧️ Last 5 NOWCAST Posts Mentioning Idukki</h1>
        """

        for index, post in enumerate(posts, start=1):

            html += f"""
            <div class="card">

                <div class="title">
                    NOWCAST #{index}
                </div>

                <p>
                    <span class="label">
                        Date & Time Posted in FB:
                    </span><br>
                    {post["fb_post_datetime"]}
                </p>

                <p>
                    <span class="label">
                        Date of Issue:
                    </span><br>
                    {post["issue_date"]}
                </p>

                <p>
                    <span class="label">
                        Time of Issue:
                    </span><br>
                    {post["issue_time"]}
                </p>

                <p>
                    <span class="label">
                        Text:
                    </span>
                </p>

                <div class="text">
                    {post["text"]}
                </div>

            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    except Exception as e:
        return f"<h2>Error</h2><pre>{str(e)}</pre>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
