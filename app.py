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

    response = requests.get(
        IMD_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    response.raise_for_status()

    html = response.text

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

    match = re.search(
        r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs",
        info,
        re.DOTALL
    )

    if not match:
        return "Unknown"

    return f"{match.group(1)} {match.group(2)} Hrs"


def extract_valid_upto(info):

    match = re.search(
        r"Valid upto:\s*(\d{4})\s*Hrs",
        info,
        re.IGNORECASE
    )

    if not match:
        return "Unknown"

    return f"{match.group(1)} Hrs"


@app.route("/")
def home():

    return """
    <h2>IMD Kerala Nowcast Service</h2>

    <ul>
        <li><a href="/idukki">Idukki Alert</a></li>
        <li><a href="/kerala">All Kerala Districts</a></li>
    </ul>
    """


@app.route("/idukki")
def idukki():

    districts = fetch_imd_data()

    for district in districts:

        if district["district"] == "IDUKKI":

            return jsonify({
                "district": district["district"],
                "warning_level": district["warning_level"],
                "issue_time": extract_issue_time(
                    district["info"]
                ),
                "valid_upto": extract_valid_upto(
                    district["info"]
                ),
                "message": re.sub(
                    r"<.*?>",
                    "",
                    district["info"]
                )
            })

    return jsonify({
        "error": "IDUKKI not found"
    })


@app.route("/kerala")
def kerala():

    districts = fetch_imd_data()

    kerala_districts = [
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

    for district in districts:

        if district["district"] in kerala_districts:

            result.append({
                "district": district["district"],
                "warning_level": district["warning_level"],
                "issue_time": extract_issue_time(
                    district["info"]
                ),
                "valid_upto": extract_valid_upto(
                    district["info"]
                )
            })

    return jsonify(result)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )
