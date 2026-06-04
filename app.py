from flask import Flask
import os
import requests

app = Flask(__name__)

DATASET_ID = "NYyRqc7fTqJQwsvDJ"


def get_latest_nowcast():
    token = os.getenv("APIFY_TOKEN")

    url = (
        f"https://api.apify.com/v2/datasets/"
        f"{DATASET_ID}/items"
        f"?token={token}"
        f"&clean=true"
        f"&limit=20"
    )

    response = requests.get(url)
    response.raise_for_status()

    posts = response.json()

    for post in posts:
        text = post.get("text", "")

        if "NOWCAST" in text.upper():
            return post

    return None


def contains_idukki(post):
    text = post.get("text", "").lower()

    return (
        "idukki" in text or
        "ഇടുക്കി" in text
    )


@app.route("/")
def home():
    return "Weather Alert Service Running"


@app.route("/check")
def check():

    nowcast = get_latest_nowcast()

    if not nowcast:
        return {
            "status": "no_nowcast_found"
        }

    return {
        "status": "success",
        "time": nowcast.get("time"),
        "url": nowcast.get("url"),
        "contains_idukki": contains_idukki(nowcast),
        "text": nowcast.get("text")
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
