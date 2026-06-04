from flask import Flask
import os
import requests
import json
import re

app = Flask(__name__)

DATASET_ID = "NYyRqc7fTqJQwsvDJ"


def get_posts(limit=50):
    token = os.getenv("APIFY_TOKEN")

    if not token:
        raise Exception("APIFY_TOKEN not configured")

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
    return "NOWCAST - " in text.upper()


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

    # Malayalam section fallback
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


def get_latest_idukki_nowcast():

    posts = get_posts(50)

    for post in posts:

        if not is_nowcast(post):
            continue

        if not contains_idukki(post):
            continue

        issue_date, issue_time = extract_issue_datetime(
            post.get("text", "")
        )

        return {
            "fb_post_time": post.get("time"),
            "issue_date": issue_date,
            "issue_time": issue_time,
            "url": post.get("url"),
            "likes": post.get("likes"),
            "shares": post.get("shares"),
            "text": post.get("text")
        }

    return None


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
            "fb_post_time": post.get("time"),
            "issue_date": issue_date,
            "issue_time": issue_time,
            "url": post.get("url"),
            "likes": post.get("likes"),
            "shares": post.get("shares")
        })

        if len(results) >= 5:
            break

    return results


@app.route("/")
def home():
    return "Weather Alert Service Running"


@app.route("/check")
def check():

    try:

        post = get_latest_idukki_nowcast()

        if not post:
            return {
                "status": "no_idukki_nowcast_found"
            }

        return app.response_class(
            response=json.dumps(
                {
                    "status": "success",
                    "contains_idukki": True,
                    "fb_post_time": post["fb_post_time"],
                    "issue_date": post["issue_date"],
                    "issue_time": post["issue_time"],
                    "url": post["url"],
                    "likes": post["likes"],
                    "shares": post["shares"],
                    "text": post["text"]
                },
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

        return app.response_class(
            response=json.dumps(
                {
                    "count": len(posts),
                    "posts": posts
                },
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
