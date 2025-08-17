# test/test_webhook.py

import json
from types import SimpleNamespace
import responses
import importlib

# ---------- helpers to build payloads ----------
def cw_webhook_payload(summary,ticket_id):
    entity = {"summary": summary, "id": ticket_id}
    return {"Entity": json.dumps(entity)}

def cw_notes_body(transcript_text):
    note_text = f"some header stuff --- Google transcription result ---\n{transcript_text}"
    return [{"text": note_text}]

# ---------- google.auth default fake ----------
class FakeCredentials:
    def __init__(self):
        self.token = "fake-token"
    def refresh(self, request):
        self.token = "fake-token-refreshed"

def patch_google_auth(monkeypatch, app_module):
    # monkeypatch google.auth.default to return our fake creds
    import google.auth

    def fake_default(scopes=None):
        return (FakeCredentials(), None)

    monkeypatch.setattr(app_module, "default", fake_default())

# ---------- Twilio fake ----------
class FakeTwilioMessage:
    sid = "SMxxxxxxx"

class FakeTwilioClient:
    def __init__(self, sid, token):
        self.message = self

    def create(self, from_=None, body=None, to=None):
        return FakeTwilioMessage

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
    pass

    # 1) Mock ConnectWise GET /notes

    # 2) Mock google.auth.default & Vertex AI POST

    # 3) Mock Twilio client

    # 4) Call webhook

    # 5) DB assertion
    # Ensure one Voicemails row created with this ticket_id

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
    patch_google_auth(monkeypatch, app_module)
    patch_twilio(monkeypatch, app_module)

    payload = cw_webhook_payload("Voicemail for xx", ticket_id)
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "processed"

    # No db rows should be created
    with app_module.app.app_context():
        rows = app_module.Voicemails.query.all()
        assert len(rows) == 0

