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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
