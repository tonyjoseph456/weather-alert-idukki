from flask import Flask, render_template_string
from datetime import datetime
from html import unescape
import requests
import re

app = Flask(__name__)

IMD_URL = "https://mausam.imd.gov.in/imd_latest/contents/districtwisewarnings_mc.php?id=4"

COLOR_MAP = {
    "#008000": "GREEN",
    "#ffff00": "YELLOW",
    "#ffa500": "ORANGE",
    "#ff0000": "RED"
}


def clean_warning_text(info):

    text = unescape(info)

    text = text.replace("\\/", "/")

    text = text.replace("<p>", "")
    text = text.replace("</p>", "")

    text = text.replace("</br>", "\n")
    text = text.replace("<br>", "\n")
    text = text.replace("<br/>", "\n")
    text = text.replace("<br />", "\n")

    text = re.sub(
        r"Time of issue:.*",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def extract_issue_time(info):

    match = re.search(
        r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs",
        info,
        re.DOTALL | re.IGNORECASE
    )

    if not match:
        return "Unknown"

    try:
        dt = datetime.strptime(
            f"{match.group(1)} {match.group(2)}",
            "%Y-%m-%d %H%M"
        )

        return dt.strftime("%d %b %Y, %I:%M %p")

    except Exception:
        return "Unknown"


def extract_valid_upto(info):

    match = re.search(
        r"Valid upto:\s*(\d{4})\s*Hrs",
        info,
        re.IGNORECASE
    )

    if not match:
        return "Unknown"

    try:
        dt = datetime.strptime(
            match.group(1),
            "%H%M"
        )

        return dt.strftime("%I:%M %p")

    except Exception:
        return "Unknown"


def fetch_imd_data():

    response = requests.get(
        IMD_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
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
        info = match.group(4)

        districts.append({
            "district": district,
            "warning_level": COLOR_MAP.get(color, color),
            "color": color,
            "info": info
        })

    return districts


@app.route("/")
def dashboard():

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

    all_districts = fetch_imd_data()

    districts = []

    for d in all_districts:

        if d["district"] in kerala_districts:

            districts.append({
                "district": d["district"],
                "warning_level": d["warning_level"],
                "issue_time": extract_issue_time(d["info"]),
                "valid_upto": extract_valid_upto(d["info"]),
                "message": clean_warning_text(d["info"])
            })

    last_refreshed = datetime.now().strftime(
        "%d %b %Y, %I:%M:%S %p"
    )

    return render_template_string(
        HTML_TEMPLATE,
        districts=districts,
        last_refreshed=last_refreshed
    )


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Kerala Nowcast Dashboard</title>

<style>

body{
    margin:0;
    font-family:Segoe UI,Arial,sans-serif;
    background:#eef2f7;
}

.header{
    background:linear-gradient(135deg,#071b44,#0c2c69);
    color:white;
    padding:35px;
    text-align:center;
}

.header h1{
    margin:0;
    font-size:48px;
}

.header p{
    margin-top:12px;
    opacity:.9;
}

.container{
    max-width:1000px;
    margin:auto;
    padding:25px;
}

.refresh{
    text-align:center;
    color:#64748b;
    margin-bottom:20px;
    font-size:18px;
}

.card{
    background:white;
    border-radius:20px;
    padding:20px;
    margin-bottom:20px;
    box-shadow:0 6px 20px rgba(0,0,0,.08);
}

select{
    width:100%;
    padding:15px;
    font-size:18px;
    border-radius:12px;
}

.badge{
    text-align:center;
    font-size:42px;
    font-weight:bold;
    padding:30px;
    border-radius:15px;
}

.green{
    background:#2e7d32;
    color:white;
}

.yellow{
    background:#ffeb3b;
    color:black;
}

.orange{
    background:#ff9800;
    color:white;
}

.red{
    background:#d32f2f;
    color:white;
}

.grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin-bottom:20px;
}

.small-card{
    background:white;
    border-radius:15px;
    padding:18px;
    box-shadow:0 2px 10px rgba(0,0,0,.08);
}

.label{
    color:#666;
    font-size:14px;
}

.value{
    font-size:24px;
    font-weight:bold;
    margin-top:8px;
}

.message{
    white-space:pre-wrap;
    line-height:1.8;
    font-size:18px;
}

.footer{
    text-align:center;
    color:#666;
    margin-top:20px;
}

@media(max-width:768px){

    .grid{
        grid-template-columns:1fr;
    }

    .header h1{
        font-size:30px;
    }

    .badge{
        font-size:28px;
    }
}

</style>

</head>

<body>

<div class="header">
    <h1>🌧 Kerala Nowcast Dashboard</h1>
    <p>India Meteorological Department (IMD)</p>
</div>

<div class="container">

    <div class="refresh">
        Last Refreshed: {{ last_refreshed }}
    </div>

    <div class="card">

        <h3>Select District</h3>

        <select id="districtSelect"></select>

    </div>

    <div id="dashboard"></div>

    <div class="footer">
        Auto refresh every 5 minutes
    </div>

</div>

<script>

const districts = {{ districts|tojson }};

const select = document.getElementById("districtSelect");
const dashboard = document.getElementById("dashboard");

districts.forEach(d => {

    const option = document.createElement("option");

    option.value = d.district;
    option.textContent = d.district;

    if(d.district === "IDUKKI"){
        option.selected = true;
    }

    select.appendChild(option);
});

function renderDistrict(name){

    const d = districts.find(
        x => x.district === name
    );

    const cls =
        d.warning_level.toLowerCase();

    dashboard.innerHTML = `

    <div class="card">
        <div class="badge ${cls}">
            ${d.warning_level}
        </div>
    </div>

    <div class="grid">

        <div class="small-card">
            <div class="label">Issue Time</div>
            <div class="value">${d.issue_time}</div>
        </div>

        <div class="small-card">
            <div class="label">Valid Until</div>
            <div class="value">${d.valid_upto}</div>
        </div>

        <div class="small-card">
            <div class="label">District</div>
            <div class="value">${d.district}</div>
        </div>

    </div>

    <div class="card">

        <h3>Warning Details</h3>

        <div class="message">
${d.message}
        </div>

    </div>
    `;
}

select.addEventListener(
    "change",
    () => renderDistrict(select.value)
);

renderDistrict("IDUKKI");

setTimeout(() => {
    location.reload();
}, 300000);

</script>

</body>
</html>
"""


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )
