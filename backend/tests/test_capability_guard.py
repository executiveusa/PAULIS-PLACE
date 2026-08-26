from services.capability_guard import redact_secrets


def test_redact_secrets_removes_nested_secret_fields():
    payload = {
        "api_key": "secret",
        "nested": {"authorization": "Bearer abc", "safe": "ok"},
        "items": [{"token": "xyz", "name": "kept"}],
    }
    redacted = redact_secrets(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["authorization"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "ok"
    assert redacted["items"][0]["token"] == "[REDACTED]"
    assert redacted["items"][0]["name"] == "kept"


def test_redact_secrets_preserves_non_secret_structure():
    payload = {"mission": {"id": "1"}, "capabilities": ["etsy.draft"]}
    assert redact_secrets(payload) == payload
