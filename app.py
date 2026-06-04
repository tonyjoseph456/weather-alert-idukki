from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Railway Weather Alert Service Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    print("HEADERS:", dict(request.headers))
    print("RAW:", request.data.decode("utf-8"))
    return {"ok": True}
