from flask import Flask, request, jsonify
import json
import os

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
        import requests

        cw_company_id = os.getenv("company_id")
        cw_manage_url = os.getenv("manage_url")
        cw_client_id = os.getenv("client_id")
        cw_public_key = os.getenv("public_key")
        cw_private_key = os.getenv("private_key")

        base_url = f"{cw_manage_url}/v2022_1/apis/3.0"
        headers = {
            "clientId": cw_client_id,
            "Authorization": f"Basic {cw_public_key}+{cw_private_key}",
            "Content-Type": "application/json"
        }

        note_url = f"{base_url}/service/tickets/{ticket_id}/notes"
        response = requests.get(note_url, headers=headers)

        if response.status_code == 200:
            notes = response.json()
            if notes:
                print("First Note:", notes[0])
            else:
                print("No notes found.")
        else:
            print("Failed to fetch notes:", response.text)

        # todo need to call Vertex API to detect urgency

        # todo need to call Twilio API to send text
        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

@app.route("/")
def home():
    return "hello world, this is test adding more, lets see if CICD working."
