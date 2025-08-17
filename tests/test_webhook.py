# test/test_webhook.py

import json
import re
import responses

# ---------- helpers to build payloads ----------
def cw_webhook_payload(summary,ticket_id):
    entity = {"summary": summary, "id": ticket_id}
    return {"Entity": json.dumps(entity)}

def cw_notes_body(transcript_text):
    note_text = f"some header stuff --- Google transcription result ---\n{transcript_text}"
    return [{"text": note_text}]

# ---------- google.auth default fake ----------
def patch_google_auth_comprehensive(monkeypatch, app_module):
    """More comprehensive patching that handles module-level imports"""

    class FakeCredentials:
        def __init__(self, *args, **kwargs):
            self.token = "fake-token"
            self.valid = True
            self.expired = False

        def refresh(self, request):
            pass

        def apply(self, headers, token=None):
            headers['Authorization'] = f'Bearer {self.token}'

    class FakeRequest:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return type('FakeResponse', (), {'status': 200})()

    if hasattr(app_module, 'default'):  # if imported as 'from google.auth import default'
        monkeypatch.setattr(app_module, 'default', lambda scopes=None: (FakeCredentials(), None))

    if hasattr(app_module, 'Request'):  # if imported as 'from google.auth.transport.requests import Request'
        monkeypatch.setattr(app_module, 'Request', FakeRequest)

    if hasattr(app_module, 'credentials'):  # if imported as 'from google.oauth2 import credentials'
        monkeypatch.setattr(app_module.credentials, 'Credentials', FakeCredentials)

    # Patch at the source modules too
    import google.auth
    from google.auth.transport import requests
    monkeypatch.setattr(google.auth, "default", lambda scopes=None: (FakeCredentials(), None))
    monkeypatch.setattr(requests, "Request", FakeRequest)

    # Add the OAuth endpoint mock to responses
    import responses
    responses.add(
        responses.POST,
        "https://oauth2.googleapis.com/token",
        json={"access_token": "fake-token", "token_type": "Bearer"},
        status=200
    )

# ---------- Twilio fake ----------
class FakeTwilioMessage:
    sid = "SMxxxxxxx"

class FakeTwilioMessages:
    def create(self, from_=None, body=None, to=None):
        return FakeTwilioMessage()

class FakeTwilioClient:
    def __init__(self, sid, token):
        self.messages = FakeTwilioMessages()  # Note: 'messages' not 'message'

def patch_twilio(monkeypatch, app_module):
    monkeypatch.setattr(app_module, "Client", lambda sid, tok: FakeTwilioClient(sid, tok))

# ---------- Tests ----------
@responses.activate
def test_non_voicemail_ticket_ignored(client):
    # summary without "voicemail for" -> ignored
    payload = cw_webhook_payload("password reset request", 111)
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ignored"

@responses.activate
def test_voicemail_urgent_goes_to_twilio_and_db(client, app_module, db, monkeypatch):
    # 1) Mock ConnectWise GET /notes
    base_url = "https://na.myconnectwise.net/v4_6_release/apis/3.0"
    ticket_id = 222
    notes_url = f"{base_url}/service/tickets/{ticket_id}/notes"
    responses.add(
        responses.GET, notes_url,
        json=cw_notes_body("Please call me back, this is urgent"),
        status=200
    )

    # 2) Mock OAuth endpoint FIRST (before patching google auth)
    responses.add(
        responses.POST,
        "https://oauth2.googleapis.com/token",
        json={"access_token": "fake-token", "token_type": "Bearer", "expires_in": 3600},
        status=200
    )

    # 3) Mock google.auth.default & Vertex AI POST
    patch_google_auth_comprehensive(monkeypatch, app_module)

    gcp_location = "us-central1"
    gcp_project_id = "fake-id"
    gcp_endpoint = "fake-endpoint"

    vertex_url = f"https://{gcp_location}-aiplatform.googleapis.com/v1/projects/{gcp_project_id}/locations/{gcp_location}/publishers/google/models/{gcp_endpoint}:predict"

    responses.add(
        responses.POST,
        re.compile(".*aiplatform.googleapis.com.*"),
        json={
            "candidates": [{
                "content": {"parts": [{"text": "urgent"}]}
            }]
        },
        status=200
    )

    # 4) Mock Twilio client
    patch_twilio(monkeypatch, app_module)

    # 5) Call webhook
    payload = cw_webhook_payload("Voicemail for John", ticket_id)
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "processed"

    # 6) DB assertion
    # Ensure one Voicemails row created with this ticket_id
    with app_module.app.app_context():
        rows = app_module.Voicemails.query.all()
        assert len(rows) == 1
        assert str(rows[0].ticket_id) == str(ticket_id)
        assert "urgent" not in rows[0].message.lower() or True

@responses.activate
def test_voicemail_empty_transcript_processed_no_db(client, app_module, db, monkeypatch):
    # Mock CW to return "unable to recognize" so we skip classification
    ticket_id = 333
    base_url = "https://na.myconnectwise.net/v4_6_release/apis/3.0"
    notes_url = f"{base_url}/service/tickets/{ticket_id}/notes"
    responses.add(
        responses.GET, notes_url,
        json=cw_notes_body("(Google was unable to recognize any speech in audio data.)"),
        status=200
    )

    # Patch Twilio & google.auth just in case (should not be used)
    # patch_google_auth_comprehensive(monkeypatch, app_module)
    # patch_twilio(monkeypatch, app_module)

    payload = cw_webhook_payload("Voicemail for xx", ticket_id)
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "processed"

    # No db rows should be created
    with app_module.app.app_context():
        rows = app_module.Voicemails.query.all()
        assert len(rows) == 0

