from flask import Flask, render_template_string
from datetime import datetime, timedelta
from html import unescape
import requests
import re
import os
import json

app = Flask(__name__)

IMD_URL = "https://mausam.imd.gov.in/imd_latest/contents/districtwisewarnings_mc.php?id=4"

COLOR_MAP = {
    "#008000": "GREEN",
    "#ffff00": "YELLOW",
    "#ffa500": "ORANGE",
    "#ff0000": "RED"
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "last_alert.json"


def clean_warning_text(info):
    text = unescape(info)
    text = text.replace("\\/", "/")
    text = text.replace("<p>", "").replace("</p>", "")
    text = text.replace("</br>", "\n").replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = re.sub(r"Time of issue:.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()

def extract_issue_time(info):
    m = re.search(r"Time of issue:\s*(\d{4}-\d{2}-\d{2}).*?(\d{4})\s*Hrs", info, re.DOTALL | re.IGNORECASE)
    if not m:
        return "Unknown"
    try:
        dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H%M")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return "Unknown"

def extract_valid_upto(info):
    m = re.search(r"Valid upto:\s*(\d{4})\s*Hrs", info, re.IGNORECASE)
    if not m:
        return "Unknown"
    try:
        dt = datetime.strptime(m.group(1), "%H%M")
        return dt.strftime("%I:%M %p")
    except:
        return "Unknown"

def fetch_imd_data():
    html = requests.get(IMD_URL, headers={"User-Agent":"Mozilla/5.0"}, timeout=30).text

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
            "info": info
        })
    return districts

    
    
def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        return False

    try:

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=30
        )

        return True

    except Exception as e:

        print(e)

        return False


def load_last_alert():

    try:

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return {
            "last_alert": "",
            "last_check": ""
        }


def save_last_alert(alert):

    ist_now = (
        datetime.utcnow()
        + timedelta(hours=5, minutes=30)
    )

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            {
                "last_alert": alert,
                "last_check": ist_now.strftime(
                    "%d %b %Y, %I:%M:%S %p IST"
                )
            },
            f
        )
        
def save_check_time():

    state = load_last_alert()

    ist_now = (
        datetime.utcnow()
        + timedelta(hours=5, minutes=30)
    )

    state["last_check"] = ist_now.strftime(
        "%d %b %Y, %I:%M:%S %p IST"
    )

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(state, f)

@app.route("/test-alert")
def test_alert():

    send_telegram(
        "🔔 TEST ALERT\n\nTelegram notification test from Railway."
    )

    return {
        "status": "test_sent"
    }
    
@app.route("/check-alert")
def check_alert():

    save_check_time()
    for d in fetch_imd_data():

        if d["district"] != "IDUKKI":
            continue

        message = clean_warning_text(d["info"])

        text = message.lower()

        keywords = [
            "thunderstorm",
            "thunderstorms",
            "lightning",
            "heavy rain",
            "very heavy rain", 
            "light rain"
        ]

        found = any(
            keyword in text
            for keyword in keywords
        )

        if not found:

            return {
                "status": "no_alert"
            }

        state = load_last_alert()

        if state["last_alert"] == message:

            return {
                "status": "already_sent"
            }

        ist_now = (
            datetime.utcnow()
            + timedelta(hours=5, minutes=30)
        )

        telegram_message = (
            "⚠️ IDUKKI WEATHER ALERT ⚠️\n\n"
            f"{message}\n\n"
            f"Checked: "
            f"{ist_now.strftime('%d %b %Y, %I:%M %p IST')}"
        )

        send_telegram(
            telegram_message
        )

        save_last_alert(
            message
        )

        return {
            "status": "alert_sent"
        }

    return {
        "status": "district_not_found"
    }

@app.route("/")
def dashboard():

    kerala = ["THIRUVANANTHAPURAM","KOLLAM","PATHANAMTHITTA","ALAPPUZHA","KOTTAYAM","IDUKKI",
              "ERNAKULAM","THRISSUR","PALAKKAD","MALAPPURAM","KOZHIKODE","WAYANAD","KANNUR","KASARAGOD"]

    state = load_last_alert()

    last_check = state.get(
        "last_check",
        "Never"
    )

    districts = []

    yellow_districts = []
    orange_districts = []
    red_districts = []

    for d in fetch_imd_data():

        if d["district"] not in kerala:
            continue

        district_data = {
            "district": d["district"],
            "warning_level": d["warning_level"],
            "issue_time": extract_issue_time(d["info"]),
            "valid_upto": extract_valid_upto(d["info"]),
            "message": clean_warning_text(d["info"])
        }

        districts.append(district_data)

        if d["warning_level"] == "YELLOW":
            yellow_districts.append(d["district"])

        elif d["warning_level"] == "ORANGE":
            orange_districts.append(d["district"])

        elif d["warning_level"] == "RED":
            red_districts.append(d["district"])

        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        last_refreshed = ist_now.strftime("%d %b %Y, %I:%M:%S %p IST")

    return render_template_string("""
<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kerala Nowcast Dashboard</title>
<style>
body{font-family:Arial;margin:0;background:#eef2f7}
.header{background:#0c2c69;color:#fff;padding:25px;text-align:center}
.container{max-width:1400px;margin:auto;padding:20px}
.card{background:#fff;padding:20px;border-radius:16px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,.1)}
select{width:100%;padding:12px}
.badge{font-size:34px;font-weight:bold;text-align:center;padding:20px;border-radius:12px}
.green{background:#2e7d32;color:#fff}.yellow{background:#ffeb3b;color:#000}
.orange{background:#fb8c00;color:#fff}.red{background:#d32f2f;color:#fff}
.grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin-bottom:25px;
}
.small{background:#fff;padding:15px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.message{
    white-space:pre-wrap;
    line-height:1.8;
    margin-top:15px;
    padding:15px;
    background:#f8fafc;
    border-left:4px solid #1565c0;
    border-radius:8px;
}
.dashboard-layout{
    display:grid;
    grid-template-columns:250px 1fr 250px;
    gap:20px;
    align-items:start;
}

.alert-panel{
    background:#fff;
    padding:15px;
    border-radius:16px;
    box-shadow:0 4px 12px rgba(0,0,0,.1);
}

.alert-title{
    font-size:20px;
    font-weight:bold;
    text-align:center;
    padding:12px;
    border-radius:12px;
    margin-bottom:15px;
}

.alert-yellow{
    background:#ffeb3b;
}

.alert-orange{
    background:#fb8c00;
}

.alert-red{
    background:#ff0000;
    color:white;
}

.alert-link{
    display:block;
    padding:8px;
    text-decoration:none;
    color:#222;
    font-weight:bold;
    border-radius:8px;
}

.alert-link:hover{
    background:#eef2f7;
}

.bottom-panel{
    margin-top:20px;
}

@media(max-width:1200px){
    .dashboard-layout{
        grid-template-columns:1fr;
    }
}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body>
<div class="header"><h1>🌧 Kerala Nowcast Dashboard</h1></div>
<div class="container">
<p style="text-align:center;color:#666;">
    Dashboard Loaded:
    {{ last_refreshed }}
</p>

<p style="text-align:center;color:#1565c0;font-weight:bold;">
    Last IMD Alert Check:
    {{ last_check }}
</p>
<div class="dashboard-layout">

    <!-- LEFT -->

    <div class="alert-panel">

        <div class="alert-title alert-yellow">
            YELLOW ALERT DISTRICTS
        </div>

        {% for district in yellow_districts %}
            <a href="#"
               class="alert-link"
               onclick="selectDistrict('{{district}}');return false;">
                {{district}}
            </a>
        {% endfor %}

    </div>

    <!-- CENTER -->

    <div>

        <div class="card">
            <select id="district"></select>
        </div>

        <div id="content"></div>

        <div class="alert-panel bottom-panel">

            <div class="alert-title alert-red">
                RED ALERT DISTRICTS
            </div>

            {% for district in red_districts %}
                <a href="#"
                   class="alert-link"
                   onclick="selectDistrict('{{district}}');return false;">
                    {{district}}
                </a>
            {% endfor %}

        </div>

    </div>

    <!-- RIGHT -->

    <div class="alert-panel">

        <div class="alert-title alert-orange">
            ORANGE ALERT DISTRICTS
        </div>

        {% for district in orange_districts %}
            <a href="#"
               class="alert-link"
               onclick="selectDistrict('{{district}}');return false;">
                {{district}}
            </a>
        {% endfor %}

    </div>

</div>
</div>
<script>
const districts={{districts|tojson}};
const sel=document.getElementById('district');
districts.forEach(d=>{
 let o=document.createElement('option');
 o.value=d.district;o.textContent=d.district;
 if(d.district==='IDUKKI') o.selected=true;
 sel.appendChild(o);
});
function render(name){
 const d=districts.find(x=>x.district===name);
 const cls=d.warning_level.toLowerCase();
 document.getElementById('content').innerHTML=`
 <div class="card"><div class="badge ${cls}">${d.warning_level}</div></div>
 <div class="grid">
 <div class="small"><b>Issue Time</b><br>${d.issue_time}</div>
 <div class="small"><b>Valid Until</b><br>${d.valid_upto}</div>
 <div class="small"><b>District</b><br>${d.district}</div>
 </div>
 <div class="card"><h3>Warning Details</h3><div class="message">${d.message}</div></div>`;
}
function selectDistrict(name){
    sel.value=name;
    render(name);

    window.scrollTo({
        top:0,
        behavior:"smooth"
    });
}
sel.onchange=()=>render(sel.value);
render('IDUKKI');
setTimeout(()=>location.reload(),300000);
</script></body></html>
""",
    districts=districts,
    yellow_districts=yellow_districts,
    orange_districts=orange_districts,
    red_districts=red_districts,
    last_refreshed=last_refreshed,
    last_check=last_check
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
