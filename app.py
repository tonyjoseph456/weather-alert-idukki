from flask import Flask, render_template_string
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

        clean_message = re.sub(
            r"<.*?>",
            "",
            d["info"]
        )

        districts.append({
            "district": d["district"],
            "warning_level": d["warning_level"],
            "issue_time": extract_issue_time(d["info"]),
            "valid_upto": extract_valid_upto(d["info"]),
            "message": clean_message
        })

return render_template_string("""


<!DOCTYPE html>

<html>
<head>

<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Kerala Nowcast Dashboard</title>

<style>

body{
    margin:0;
    padding:20px;
    font-family:Arial,sans-serif;
    background:#eef3f8;
}

.container{
    max-width:850px;
    margin:auto;
}

.header{
    text-align:center;
    margin-bottom:20px;
}

.header h1{
    color:#1565c0;
    margin-bottom:5px;
}

.card{
    background:white;
    border-radius:18px;
    padding:25px;
    box-shadow:0 5px 25px rgba(0,0,0,0.12);
}

select{
    width:100%;
    padding:14px;
    font-size:18px;
    border-radius:10px;
}

.alert{
    font-size:32px;
    font-weight:bold;
    text-align:center;
    margin-top:20px;
}

.green{
    color:#008000;
}

.yellow{
    color:#c9a000;
}

.orange{
    color:#ff8800;
}

.red{
    color:#d60000;
}

.label{
    font-weight:bold;
}

.info-row{
    margin-top:15px;
}

.message{
    background:#f8f8f8;
    padding:15px;
    border-radius:10px;
    margin-top:10px;
    white-space:pre-wrap;
    line-height:1.6;
}

.footer{
    text-align:center;
    color:#666;
    margin-top:20px;
    font-size:14px;
}

</style>

</head>

<body>

<div class="container">

<div class="header">
    <h1>🌧 Kerala Nowcast Dashboard</h1>
    <p>Select a district to view the latest IMD nowcast.</p>
</div>

<div class="card">

<select id="districtSelect"></select>

<div id="content"></div>

</div>

</div>

<script>

const districts = {{ districts|tojson }};

const select = document.getElementById("districtSelect");
const content = document.getElementById("content");

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

    const d = districts.find(x => x.district === name);

    let cls = d.warning_level.toLowerCase();

    content.innerHTML = `
        <div class="alert ${cls}">
            ${d.warning_level}
        </div>

        <div class="info-row">
            <span class="label">🕒 Issue Time:</span><br>
            ${d.issue_time}
        </div>

        <div class="info-row">
            <span class="label">⏰ Valid Until:</span><br>
            ${d.valid_upto}
        </div>

        <div class="info-row">
            <span class="label">📝 Warning Details:</span>
        </div>

        <div class="message">
            ${d.message}
        </div>

        <div class="footer">
            Data Source: IMD Nowcast | Auto refresh every 5 minutes
        </div>
    `;
}

select.addEventListener("change", () => {
    renderDistrict(select.value);
});

renderDistrict("IDUKKI");

setTimeout(() => {
    location.reload();
}, 300000);

</script>

</body>
</html>
    """, districts=districts)

if **name** == "**main**":
app.run(
host="0.0.0.0",
port=8080
)
