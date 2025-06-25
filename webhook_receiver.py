from flask import Flask, request, jsonify
import json
import os
from pyconnectwise import ConnectWiseManageAPIClient

company_id = os.getenv("company_id")
manage_url = os.getenv("manage_url")
client_id = os.getenv("client_id")
public_key = os.getenv("public_key")
private_key = os.getenv("private_key")
# manage_api_client = ConnectWiseManageAPIClient(company_id, manage_url, client_id, public_key, private_key)

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
    ticket_id = entity.get("id", "")

    if "voicemail for" in ticket_title:
        print("Voicemail ticket detected:", ticket_title)
        # todo need to call API to extract the note
        # ticket_initial_note = manage_api_client.service.tickets.id(ticket_id).notes.get()[0]
        # print("Detail:", ticket_initial_note)

        # todo need to call Vertex API to detect urgency

        # todo need to call Twilio API to send text
        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

@app.route("/")
def home():
    return "hello world, this is test adding more, lets see if CICD working."
