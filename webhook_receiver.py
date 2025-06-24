from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json

    # Logging for testing
    print("Received raw webhook data:", data)

    entity_str = data.get("Entity")
    if not entity_str:
        print("No 'Entity' field in payload.")
        return jsonify({"status": "invalid"}), 400

    try:
        # Parse the stringified JSON in "Entity"
        entity = json.loads(entity_str)
    except json.JSONDecodeError:
        print("Failed to parse 'Entity'.")
        return jsonify({"status": "error parsing entity"}), 400

    # Extract ticket title
    ticket_title = entity.get("summary", "").lower()

    if "voicemail for" in ticket_title:
        print("Voicemail ticket detected:", ticket_title)
        # Run urgency model, store result, etc.
        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

@app.route("/")
def home():
    return "hello world, this is test adding more, lets see if CICD working."
