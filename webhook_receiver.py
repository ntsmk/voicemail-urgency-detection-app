from flask import Flask, request, jsonify
import os
import json

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

        import requests
        import base64

        cw_company_id = os.getenv("company_id")
        cw_manage_url = os.getenv("manage_url")
        cw_client_id = os.getenv("client_id")
        cw_public_key = os.getenv("public_key")
        cw_private_key = os.getenv("private_key")

        auth_str = f"{cw_company_id}+{cw_public_key}:{cw_private_key}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        base_url = f"https://{cw_manage_url}/v2022_1/apis/3.0"
        headers = {
            "clientId": cw_client_id,
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }

        note_url = f"{base_url}/service/tickets/{ticket_id}/notes"
        try:
            response = requests.get(note_url, headers=headers)
            if response.status_code == 200:
                notes = response.json()
                if notes:
                    print("First Note:", notes[0])
                else:
                    print("No notes found.")
            else:
                print("Failed to fetch notes:", response.text)
        except requests.exceptions.RequestException as e:
            print("API request failed:", str(e))
            return jsonify({"status": "api_error", "error": str(e)}), 500

        return jsonify({"status": "processed"}), 200
    else:
        print("Skipping non-voicemail ticket:", ticket_title)
        return jsonify({"status": "ignored"}), 200

# todo need to work on this test route until I get proper results
@app.route("/test_notes/<ticket_id>")
def test_notes(ticket_id):
    # Your code to call ConnectWise API and print result
    print("Voicemail ticket detected: This is test route")

    import requests
    import base64

    cw_company_id = os.getenv("company_id")
    cw_manage_url = os.getenv("manage_url")
    cw_client_id = os.getenv("client_id")
    cw_public_key = os.getenv("public_key")
    cw_private_key = os.getenv("private_key")

    auth_str = f"{cw_company_id}+{cw_public_key}:{cw_private_key}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    base_url = f"https://{cw_manage_url}/v2022_1/apis/3.0"
    headers = {
        "clientId": cw_client_id,
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json"
    }
    note_url = f"{base_url}/service/tickets/{ticket_id}/notes"

    try:
        response = requests.get(note_url, headers=headers)
        print("executed .get here")

        if response.status_code == 200:
            notes = response.json()
            if notes:
                print("First Note:", notes[0])
            else:
                print("No notes found.")
        else:
            print("Failed to fetch notes:", response.text)
    except requests.exceptions.RequestException as e:
        print("API request failed:", str(e))
        return jsonify({"status": "api_error", "error": str(e)}), 500

    return "Check logs!"

@app.route("/")
def home():
    return "webhook is up"
