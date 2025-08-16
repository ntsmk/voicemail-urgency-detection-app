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

    def fake_default(scopes=None)
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
    pass

@responses.activate
def test_voicemail_urgent_goes_to_twilio_and_db(client, app_module, db, monkeypatch):
    pass

@responses.activate
def test_voicemail_empty_transcript_processed_no_db(client, app_module, db, monkeypatch):
    pass
