from flask import Flask
import requests
import os

app = Flask(__name__)

DATASET_ID = "NYyRqc7fTqJQwsvDJ"

@app.route("/")
def home():
    return "Railway Weather Alert Service Running"

@app.route("/check")
def check():

    token = os.getenv("APIFY_TOKEN")

    url = (
        f"https://api.apify.com/v2/datasets/"
        f"{DATASET_ID}/items"
        f"?token={token}"
        f"&clean=true"
        f"&limit=1"
    )

    response = requests.get(url)

    print(response.text)

    return response.text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
