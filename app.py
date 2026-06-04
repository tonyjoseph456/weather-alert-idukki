import os
import requests

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


if __name__ == "__main__":

    nowcast = get_latest_nowcast()

    if not nowcast:
        print("No NOWCAST post found")
        exit()

    print("\n===== LATEST NOWCAST =====\n")

    print("Time:")
    print(nowcast.get("time"))

    print("\nURL:")
    print(nowcast.get("url"))

    print("\nContains Idukki:")
    print(contains_idukki(nowcast))

    print("\nPost Text:")
    print(nowcast.get("text"))
