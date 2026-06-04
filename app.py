from flask import Flask
import os
import requests
import json

app = Flask(__name__)

# Your Dataset ID
DATASET_ID = "NYyRqc7fTqJQwsvDJ"


def get_latest_nowcast():
    token = os.getenv("APIFY_TOKEN")

    if not token:
        raise Exception("APIFY_TOKEN environment variable not found")

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

    try:
        nowcast = get_latest_nowcast()

        if not nowcast:
            return {
                "status": "no_nowcast_found"
            }

        return app.response_class(
            response=json.dumps(
                {
                    "status": "success",
                    "contains_idukki": contains_idukki(nowcast),
                    "time": nowcast.get("time"),
                    "url": nowcast.get("url"),
                    "text": nowcast.get("text")
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


@app.route("/nowcast")
def nowcast():

    try:
        post = get_latest_nowcast()

        if not post:
            return "No NOWCAST found"

        return f"""
        <html>
        <head>
            <title>Latest NOWCAST</title>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial; max-width: 1000px; margin: auto; padding: 20px;">
            <h2>Latest NOWCAST</h2>

            <p><b>Idukki Mentioned:</b> {contains_idukki(post)}</p>

            <p><b>Time:</b> {post.get('time')}</p>

            <p>
                <b>Facebook Post:</b><br>
                <a href="{post.get('url')}" target="_blank">
                    Open Post
                </a>
            </p>

            <hr>

            <pre style="white-space: pre-wrap; font-size: 16px;">
{post.get('text')}
            </pre>

        </body>
        </html>
        """

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
