from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json

    # Logging for testing
    print("Received webhook data:", data)

    ticket_title = data.get("summary", "").lower()

    if "voicemail for" in ticket_title:
        print("Voicemail ticket detected:", ticket_title)
        # Run urgency model, store result, etc.
        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

@app.route("/")
def home():
    return "hello world"
