from flask import Flask, request, jsonify
import os
import json
import requests
import base64

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json

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

    ticket_title = entity.get("summary", "").lower()
    ticket_id = entity.get("id", "")

    if "voicemail for" in ticket_title:
        print("Voicemail ticket detected:", ticket_title)
        cw_company_id = os.getenv("company_id")
        cw_client_id = os.getenv("client_id")
        cw_public_key = os.getenv("public_key")
        cw_private_key = os.getenv("private_key")

        auth_str = f"{cw_company_id}+{cw_public_key}:{cw_private_key}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        base_url = "https://na.myconnectwise.net/v4_6_release/apis/3.0"
        note_url = f"{base_url}/service/tickets/{ticket_id}/notes"
        headers = {
            "clientId": cw_client_id,
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(note_url, headers=headers, timeout=10)
            print("executed .get here")

            if response.status_code == 200:
                notes = response.json()
                if notes:
                    print("First Note:", notes[0])
                else:
                    print("No notes found.")
            else:
                # print(response.status_code)
                print("Failed to fetch notes:", response.text)
        except requests.exceptions.RequestException as e:
            print("API request failed:", str(e))
            return jsonify({"status": "api_error", "error": str(e)}), 500

        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

# todo add to trim the detail data in this test route
@app.route("/test_notes/<ticket_id>")
def test_notes(ticket_id):
    print("Voicemail ticket detected: This is test route")

    cw_company_id = os.getenv("company_id")
    cw_client_id = os.getenv("client_id")
    cw_public_key = os.getenv("public_key")
    cw_private_key = os.getenv("private_key")

    auth_str = f"{cw_company_id}+{cw_public_key}:{cw_private_key}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    base_url = "https://na.myconnectwise.net/v4_6_release/apis/3.0"
    note_url = f"{base_url}/service/tickets/{ticket_id}/notes"
    headers = {
        "clientId": cw_client_id,
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(note_url, headers=headers, timeout=10)
        print("executed .get here")

        if response.status_code == 200:
            notes = response.json()
            if notes:
                print("First Note:", notes[0])
                # todo fill out here
                split_note = notes[0].text.split("--- Google transcription result ---", 1)[-1].strip()
                if split_note not in ["(Google was unable to recognize any speech in audio data.)", "null",
                                        "null\nnull"]:
                    trimed_note = split_note
                else:
                    trimed_note = "this voicemail ticket is empty"
                print("Note passed to machine learning:", trimed_note)
            else:
                print("No notes found.")
        else:
            # print(response.status_code)
            print("Failed to fetch notes:", response.text)
    except requests.exceptions.RequestException as e:
        print("API request failed:", str(e))
        return jsonify({"status": "api_error", "error": str(e)}), 500

    return "Check logs!!!!"

@app.route("/")
def home():
    return "webhook is up"
