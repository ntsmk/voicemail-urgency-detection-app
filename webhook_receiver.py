from flask import Flask, request, jsonify
import os
import json
import requests
import base64
from google.auth import default
from google.auth.transport.requests import Request
from twilio.rest import Client

app = Flask(__name__)

# todo add db to store the voicemail data
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json

    print("Received raw webhook data:", data)

    # Getting ticket title and ID from data received via webhook
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

    # Checking if the ticket is voicemail ticket or not
    if "voicemail for" in ticket_title:
        print("Voicemail ticket detected:", ticket_title)

        # Calling ConnectWise API to get the detail note
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

            if response.status_code == 200:
                notes = response.json()
                if notes:
                    print("First Note:", notes[0])
                    split_note = notes[0]["text"].split("--- Google transcription result ---", 1)[-1].strip()

                    # If the voicemail record is not empty, calling Vertex AI API to detect the urgency of text
                    if split_note not in ["(Google was unable to recognize any speech in audio data.)", "null",
                                          "null\nnull"]:
                        trimmed_note = split_note
                        gcp_project_id = os.getenv("project_id")
                        gcp_location = os.getenv("location")
                        gcp_endpoint_id = os.getenv("endpoint_id")
                        URL = f"https://{gcp_location}-aiplatform.googleapis.com/v1/projects/{gcp_project_id}/locations/{gcp_location}/endpoints/{gcp_endpoint_id}:generateContent"
                        print("set credentials for machine learning")

                        # Get access token using default credentials (Application Default Credentials)
                        credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                        credentials.refresh(Request())
                        token = credentials.token

                        # Build the headers
                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }

                        # Gemini content format
                        body = {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {"text": f"{trimmed_note}"}
                                    ]
                                }
                            ],
                        }

                        # Make the POST request
                        response = requests.post(URL, headers=headers, json=body)

                        # Show result of category classification
                        result = response.json()['candidates'][0]['content']['parts'][0]['text']
                        print(result)

                        # If it is urgent category, sending text via Twilio to notify
                        if "urgent" in result:
                            print("Urgent. Sending text to notify")
                            tw_account_id = os.getenv("account_sid")
                            tw_auth_token = os.getenv("auth_token")
                            tw_from_number = os.getenv("from_number")
                            tw_to_number = os.getenv("to_number")

                            client = Client(tw_account_id, tw_auth_token)
                            message = client.messages.create(
                                from_=tw_from_number,
                                body=f"\n\nUrgency detected on voicemail ticket. \n\nTicket#:{ticket_id}\n\nDetails:{trimmed_note}",
                                to=tw_to_number
                            )
                            print("Sent")

                        else:
                            print("Not urgent")

                    else:
                        trimmed_note = "the voicemail record is empty"
                    print("Note passed to machine learning:", trimmed_note)
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

# This is a test route before trying webhook function. Try this and if works, merge it to webhook
@app.route("/test_notes/<ticket_id>")
def test_notes(ticket_id):
    print("Voicemail ticket detected: This is a test route")

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
    urgent_flag = ""
    result = ""
    try:
        response = requests.get(note_url, headers=headers, timeout=10)
        print("executed .get here")

        if response.status_code == 200:
            notes = response.json()
            if notes:
                print("First Note:", notes[0])
                split_note = notes[0]["text"].split("--- Google transcription result ---", 1)[-1].strip()
                if split_note not in ["(Google was unable to recognize any speech in audio data.)", "null",
                                        "null\nnull"]:
                    trimmed_note = split_note

                    gcp_project_id = os.getenv("project_id")
                    gcp_location = os.getenv("location")
                    gcp_endpoint_id = os.getenv("endpoint_id")
                    URL = f"https://{gcp_location}-aiplatform.googleapis.com/v1/projects/{gcp_project_id}/locations/{gcp_location}/endpoints/{gcp_endpoint_id}:generateContent"
                    print("set credentials")

                    # Get access token using default credentials (Application Default Credentials)
                    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                    credentials.refresh(Request())
                    token = credentials.token

                    # Build the headers
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }

                    # Gemini content format
                    body = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": f"{trimmed_note}"}
                                ]
                            }
                        ],
                    }

                    # Make the POST request
                    response = requests.post(URL, headers=headers, json=body)

                    # Show result
                    result = response.json()['candidates'][0]['content']['parts'][0]['text']
                    print(result)

                    if "urgent" in result:
                        print("Urgent. Send text to notify")
                        urgent_flag = "urgent"
                        tw_account_id = os.getenv("account_sid")
                        tw_auth_token = os.getenv("auth_token")
                        tw_from_number = os.getenv("from_number")
                        tw_to_number = os.getenv("to_number")

                        client = Client(tw_account_id, tw_auth_token)
                        message =client.messages.create(
                            from_=tw_from_number,
                            body=f"\n\nUrgency detected on voicemail ticket. \n\nTicket#:{ticket_id}\n\nDetails:{trimmed_note}",
                            to=tw_to_number
                        )
                        print("Sent")

                    else:
                        print("Not urgent")
                        urgent_flag = "not urgent"

                else:
                    result = "The voicemail record is empty"
                print("Note passed to machine learning:", result)
            else:
                result = "No notes found."
                print("No notes found.")
        else:
            result = "Failed to fetch voicemail ticket notes"
            print("Failed to fetch notes:", response.text)
    except requests.exceptions.RequestException as e:
        print("API request failed:", str(e))
        return jsonify({"status": "api_error", "error": str(e)}), 500

    return jsonify({
        "category": result,
        "urgency": urgent_flag
    })

@app.route("/")
def home():
    return "webhook is up"
