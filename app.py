from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Railway Weather Alert Service Running"

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    print("========== NEW WEBHOOK ==========")
    print(data)
    print("=================================")

    return jsonify({
        "status": "received"
    })
