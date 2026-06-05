from flask import Flask, jsonify
import requests
import re
from html import unescape

app = Flask(__name__)

IMD_URL = "https://mausam.imd.gov.in/imd_latest/contents/districtwisewarnings_mc.php?id=4"

COLOR_MAP = {
    "#008000": "GREEN",
    "#ffff00": "YELLOW",
    "#ffa500": "ORANGE",
    "#ff0000": "RED"
}


def fetch_imd_data():

    html = requests.get(
        IMD_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    ).text

    pattern = re.compile(
        r'"title":\s*"([^"]+)".*?'
        r'"id":\s*"([^"]+)".*?'
        r'"color":\s*"([^"]+)".*?'
        r'"info":\s*"([^"]+)"',
        re.DOTALL
    )

    districts = []

    for match in pattern.finditer(html):

        district = match.group(1)
        color = match.group(3).lower()
        info = unescape(match.group(4))

        districts.append({
            "district": district,
            "warning_level": COLOR_MAP.get(color, color),
            "color": color,
            "info": info
        })

    return districts


def extract_issue_time(info):

    m = re.search(
        r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs",
        info,
        re.DOTALL
    )

    if not m:
        return None

    return f"{m.group(1)} {m.group(2)} Hrs"


def extract_valid_upto(info):

    m = re.search(
        r"Valid upto:\s*(\d{4})\s*Hrs",
        info,
        re.IGNORECASE
    )

    if not m:
        return None

    return f"{m.group(1)} Hrs"


@app.route("/")
def home():

    return """
    <h2>IMD Kerala Nowcast Service Running</h2>

    <ul>
        <li><a href='/idukki'>/idukki</a></li>
        <li><a href='/kerala'>/kerala</a></li>
    </ul>
    """


@app.route("/idukki")
def idukki():

    districts = fetch_imd_data()

    for d in districts:

        if d["district"] == "IDUKKI":

            return jsonify({
                "district": d["district"],
                "warning_level": d["warning_level"],
                "issue_time": extract_issue_time(d["info"]),
                "valid_upto": extract_valid_upto(d["info"]),
                "message": re.sub("<.*?>", "", d["info"])
            })

    return jsonify({
        "error": "IDUKKI not found"
    })


@app.route("/kerala")
def kerala():

    districts = fetch_imd_data()

    kerala = [
        "THIRUVANANTHAPURAM",
        "KOLLAM",
        "PATHANAMTHITTA",
        "ALAPPUZHA",
        "KOTTAYAM",
        "IDUKKI",
        "ERNAKULAM",
        "THRISSUR",
        "PALAKKAD",
        "MALAPPURAM",
        "KOZHIKODE",
        "WAYANAD",
        "KANNUR",
        "KASARAGOD"
    ]

    result = []

    for d in districts:

        if d["district"] in kerala:

            result.append({
                "district": d["district"],
                "warning_level": d["warning_level"],
                "issue_time": extract_issue_time(d["info"]),
                "valid_upto": extract_valid_upto(d["info"])
            })

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
