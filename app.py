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
            "last_alert": ""
        }


def save_last_alert(alert):

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            {
                "last_alert": alert
            },
            f
        )

@app.route("/check-alert")
def check_alert():

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
            "very heavy rain"
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

    districts = []
    for d in fetch_imd_data():
        if d["district"] in kerala:
            districts.append({
                "district": d["district"],
                "warning_level": d["warning_level"],
                "issue_time": extract_issue_time(d["info"]),
                "valid_upto": extract_valid_upto(d["info"]),
                "message": clean_warning_text(d["info"])
            })

    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    last_refreshed = ist_now.strftime("%d %b %Y, %I:%M:%S %p IST")

    return render_template_string("""
<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kerala Nowcast Dashboard</title>
<style>
body{font-family:Arial;margin:0;background:#eef2f7}
.header{background:#0c2c69;color:#fff;padding:25px;text-align:center}
.container{max-width:1000px;margin:auto;padding:20px}
.card{background:#fff;padding:20px;border-radius:16px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,.1)}
select{width:100%;padding:12px}
.badge{font-size:34px;font-weight:bold;text-align:center;padding:20px;border-radius:12px}
.green{background:#2e7d32;color:#fff}.yellow{background:#ffeb3b;color:#000}
.orange{background:#fb8c00;color:#fff}.red{background:#d32f2f;color:#fff}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}
.small{background:#fff;padding:15px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.message{white-space:pre-wrap;line-height:1.7}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body>
<div class="header"><h1>🌧 Kerala Nowcast Dashboard</h1></div>
<div class="container">
<p style="text-align:center">Last Refreshed: {{last_refreshed}}</p>
<div class="card"><select id="district"></select></div>
<div id="content"></div>
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
sel.onchange=()=>render(sel.value);
render('IDUKKI');
setTimeout(()=>location.reload(),300000);
</script></body></html>
""", districts=districts, last_refreshed=last_refreshed)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
