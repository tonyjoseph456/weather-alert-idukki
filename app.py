from flask import Flask, render_template_string, request
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

PUSHOVER_STATE_FILE = "pushover_state.json"
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")

STATE_FILE = "last_alert.json"

SEVERE_KEYWORDS = [
    "thunderstorm",
    "thunderstorms",
    "lightning",
    "thundershower",
    "thunder shower",
    "thundershowers",
    "thunder showers"
]


def clean_warning_text(info):
    text = unescape(info)
    text = text.replace("\\/", "/")

    # Decode common IMD unicode escapes
    text = (
        text.replace("\\u2013", "–")
            .replace("\\u2014", "—")
            .replace("\\u00b0", "°")
    )

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


def get_alert_districts():

    yellow = []
    orange = []
    red = []

    KERALA_DISTRICTS = {
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
    }

    for d in fetch_imd_data():

        district = d["district"].upper()

        if district not in KERALA_DISTRICTS:
            continue

        if d["warning_level"] == "YELLOW":
            yellow.append(district)

        elif d["warning_level"] == "ORANGE":
            orange.append(district)

        elif d["warning_level"] == "RED":
            red.append(district)

    yellow = sorted(set(yellow))
    orange = sorted(set(orange))
    red = sorted(set(red))

    return yellow, orange, red


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
        
def send_pushover(message):

    if not PUSHOVER_APP_TOKEN or not PUSHOVER_USER_KEY:
        return False

    try:

        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": PUSHOVER_APP_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "title": "⚡ Kerala Severe Weather Alert",
                "message": message,

                # Emergency priority
                "priority": 2,
                "retry": 60,
                "expire": 3600
            },
            timeout=30
        )

        return True

    except Exception as e:

        print(e)

        return False

def send_telegram_to_chat(chat_id, message):

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message
        },
        timeout=30
    )

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
def pushover_enabled():

    try:
        with open(PUSHOVER_STATE_FILE, "r") as f:
            return json.load(f).get("enabled", True)

    except:
        return True


def set_pushover_enabled(enabled):

    with open(PUSHOVER_STATE_FILE, "w") as f:
        json.dump({"enabled": enabled}, f)


        
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

       

        state = load_last_alert()

        current_alert = (
            d["warning_level"]
            + "|"
            + extract_issue_time(d["info"])
            + "|"
            + message
        )

        state = load_last_alert()

        if state.get("last_alert") == current_alert:
            return {
                "status": "already_sent"
            }

        alert_map = {
            "GREEN": "🟢 GREEN ALERT",
            "YELLOW": "🟡 YELLOW ALERT",
            "ORANGE": "🟠 ORANGE ALERT",
            "RED": "🔴 RED ALERT"
            }

        telegram_message = f"""⚠️ IDUKKI WEATHER ALERT ⚠️

        ALERT TYPE
        {alert_map.get(d["warning_level"], d["warning_level"])}

        Issue Time: {extract_issue_time(d["info"])}
        Valid Until: {extract_valid_upto(d["info"])}

        Warning Details
        {message}
        """

        send_telegram(
        telegram_message
        )

        if (
            pushover_enabled()
            and any(
                keyword in text
                for keyword in SEVERE_KEYWORDS
            )
        ):
            send_pushover(
                telegram_message
            )

        save_last_alert(
            current_alert
        )

        return {
            "status": "alert_sent"
        }

    return {
        "status": "district_not_found"
    }

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():

    
    data = request.json
    text = data["message"]["text"]
    print("WEBHOOK HIT:", text)
    chat_id = data["message"]["chat"]["id"]
    yellow, orange, red = get_alert_districts()
    KERALA_DISTRICTS = [
    "ALAPPUZHA",
    "ERNAKULAM",
    "IDUKKI",
    "KANNUR",
    "KASARAGOD",
    "KOLLAM",
    "KOTTAYAM",
    "KOZHIKODE",
    "MALAPPURAM",
    "PALAKKAD",
    "PATHANAMTHITTA",
    "THIRUVANANTHAPURAM",
    "THRISSUR",
    "WAYANAD"
]

    green = sorted([
        d for d in KERALA_DISTRICTS
        if d not in (yellow + orange + red)
    ])
    if text == "/orange":
        msg = "🟠 Orange Alert Districts\n\n"
        if orange:
            msg += "\n".join(f"• {d}" for d in orange)
        else:
            msg += "No Orange Alerts"
        send_telegram_to_chat(chat_id, msg)
    elif text == "/green":

        msg = "🟢 Green Alert Districts\n\n"

        if green:
            msg += "\n".join(f"• {d}" for d in green)
        else:
            msg += "No Green Alert Districts"

        send_telegram_to_chat(chat_id, msg)
    elif text == "/yellow":
        msg = "🟡 Yellow Alert Districts\n\n"
        if yellow:
            msg += "\n".join(f"• {d}" for d in yellow)
        else:
            msg += "No Yellow Alerts"
        send_telegram_to_chat(chat_id, msg)
    elif text == "/red":
        msg = "🔴 Red Alert Districts\n\n"
        if red:
            msg += "\n".join(f"• {d}" for d in red)
        else:
            msg += "No Red Alerts"
        send_telegram_to_chat(chat_id, msg)
    elif text == "/all":

        msg = "🌧 KERALA ALERT STATUS\n\n"
        
        msg += "🟢 Green Alert Districts\n"
        
        if green:
            msg += "\n".join(f"• {d}" for d in green)
        else:
            msg += "No Green Alert Districts"

        msg += "\n\n"

        msg += "🟡 Yellow Alert Districts\n"

        if yellow:
            msg += "\n".join(f"• {d}" for d in yellow)
        else:
            msg += "No Yellow Alerts"

        msg += "\n\n"

        msg += "🟠 Orange Alert Districts\n"

        if orange:
            msg += "\n".join(f"• {d}" for d in orange)
        else:
            msg += "No Orange Alerts"

        msg += "\n\n"

        msg += "🔴 Red Alert Districts\n"

        if red:
            msg += "\n".join(f"• {d}" for d in red)
        else:
            msg += "No Red Alerts"

        send_telegram_to_chat(chat_id, msg)
    elif text == "/help":

        msg = (
            "🌧 Kerala Weather Bot\n\n"
            "/green - Green Alert Districts\n"
            "/yellow - Yellow Alert Districts\n"
            "/orange - Orange Alert Districts\n"
            "/red - Red Alert Districts\n"
            "/all - All Kerala Alerts\n\n"
            "/pushover_on - Enable iPhone alerts\n"
            "/pushover_off - Disable iPhone alerts\n"
            "/pushover_status - Check status\n\n"
            "District Commands:\n"
            "/alappuzha\n"
            "/ernakulam\n"
            "/idukki\n"
            "/kannur\n"
            "/kasaragod\n"
            "/kollam\n"
            "/kottayam\n"
            "/kozhikode\n"
            "/malappuram\n"
            "/palakkad\n"
            "/pathanamthitta\n"
            "/thiruvananthapuram\n"
            "/thrissur\n"
            "/wayanad\n"
        )

        send_telegram_to_chat(chat_id, msg)
    elif text == "/pushover_off":

        set_pushover_enabled(False)

        send_telegram_to_chat(
            chat_id,
            "🔕 Pushover alerts disabled"
        )

    elif text == "/pushover_on":

        set_pushover_enabled(True)

        send_telegram_to_chat(
            chat_id,
            "🔔 Pushover alerts enabled"
        )

    elif text == "/pushover_status":

        status = (
            "ON"
            if pushover_enabled()
            else "OFF"
        )

        send_telegram_to_chat(
            chat_id,
            f"📱 Pushover Alerts: {status}"
        )
    elif text.startswith("/"):
        district_name = text[1:].upper()

        for d in fetch_imd_data():

            if d["district"].upper() == district_name:

                alert_map = {
                    "GREEN": "🟢 GREEN ALERT",
                    "YELLOW": "🟡 YELLOW ALERT",
                    "ORANGE": "🟠 ORANGE ALERT",
                    "RED": "🔴 RED ALERT"
                }

                msg = f"""⚠️ {d['district']} WEATHER ALERT ⚠️

        ALERT TYPE
        {alert_map.get(d["warning_level"], d["warning_level"])}

        Issue Time: {extract_issue_time(d["info"])}
        Valid Until: {extract_valid_upto(d["info"])}

        Warning Details
        {clean_warning_text(d["info"])}
        """

                send_telegram_to_chat(chat_id, msg)

                return {"ok": True}

        send_telegram_to_chat(chat_id,f"❌ District '{district_name}' not found.")
    return {"ok": True}

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
    green_districts = []
    
    yellow_districts = sorted(yellow_districts)
    orange_districts = sorted(orange_districts)
    red_districts = sorted(red_districts)

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
    
    yellow_districts = sorted(yellow_districts)
    orange_districts = sorted(orange_districts)
    red_districts = sorted(red_districts)

    alerted_districts = set(
    yellow_districts
    + orange_districts
    + red_districts
)

    green_districts = sorted([
        d for d in kerala
        if d not in alerted_districts
    ])

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
    grid-template-areas:
        ". green ."
        "yellow center orange";
    column-gap:40px;
    row-gap:20px;
}
.left-panel{
    grid-area:yellow;
}

.center-panel{
    grid-area:center;
}

.right-panel{
    grid-area:orange;
}

.green-panel{
    grid-area:green;
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

 #refreshBtn{
        width:72px;
        height:72px;
        font-size:38px;
        bottom:16px;
        right:16px;
    }
    .green-panel{
        order:1;
    }
    
    .dashboard-layout{
        display:flex;
        flex-direction:column;
        gap:20px;
    }

    .center-panel{
        order:2;
    }

    .left-panel{
        order:3;
    }

    .right-panel{
        order:4;
    }

}
#refreshBtn{
    position:fixed;
    bottom:20px;
    right:20px;
    width:48px;
    height:48px;
    border:none;
    border-radius:24px;
    background:rgba(255,255,255,.75);
    backdrop-filter:blur(10px);
    font-size:24px;
    box-shadow:0 2px 8px rgba(0,0,0,.12);
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

<div class="alert-panel green-panel">

    <div class="alert-title"
         style="background:#228B00;color:white;">
        GREEN ALERT DISTRICTS
    </div>

    {% if green_districts %}

        {% for district in green_districts %}
            <a href="#"
               class="alert-link"
               onclick="selectDistrict('{{district}}');return false;">
               {{district}}
            </a>
        {% endfor %}

    {% else %}

        <div style="text-align:center;color:#888;padding:10px;">
            No Green Alerts
        </div>

    {% endif %}

</div>
    <!-- LEFT -->

    <div class="alert-panel left-panel">

        <div class="alert-title alert-yellow">
            YELLOW ALERT DISTRICTS
        </div>

        {% if yellow_districts %}

            {% for district in yellow_districts %}
                <a href="#"
                    class="alert-link"
                    onclick="selectDistrict('{{district}}');return false;">
                    {{district}}
                </a>
            {% endfor %}
            {% else %}

                <div style="text-align:center;color:#888;padding:10px;">
                    No Yellow Alerts
                </div>
        {% endif %}
    </div>

    <!-- CENTER -->

    <div class="center-panel">

        

        <div id="content"></div>
        <div class="alert-panel bottom-panel red-panel">

    <div class="alert-title alert-red">
        RED ALERT DISTRICTS
    </div>

    {% if red_districts %}

        {% for district in red_districts %}
            <a href="#"
                class="alert-link"
                onclick="selectDistrict('{{district}}');return false;">
            {{district}}
        </a>
        {% endfor %}
        {% else %}
            <div style="text-align:center;color:#888;padding:10px;">
                No Red Alerts
            </div>
    {% endif %}
</div>
    </div>

    <!-- RIGHT -->

    <div class="alert-panel right-panel">

        <div class="alert-title alert-orange">
            ORANGE ALERT DISTRICTS
        </div>

        {% if orange_districts %}

            {% for district in orange_districts %}
                <a href="#"
                    class="alert-link"
                    onclick="selectDistrict('{{district}}');return false;">
                    {{district}}
                </a>
            {% endfor %}
            {% else %}
                <div style="text-align:center;color:#888;padding:10px;">
                    No Orange Alerts
                </div>
        {% endif %}
    </div>
    
    
</div>

</div>
<button id="refreshBtn" onclick="location.reload()">
    ⟳
</button>
<script>
const districts={{districts|tojson}};

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
    render(name);

    window.scrollTo({
        top:0,
        behavior:"smooth"
    });
}

render('IDUKKI');
setTimeout(()=>location.reload(),120000);
</script></body></html>
""",
    districts=districts,
    green_districts=green_districts,
    yellow_districts=yellow_districts,
    orange_districts=orange_districts,
    red_districts=red_districts,
    last_refreshed=last_refreshed,
    last_check=last_check
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
