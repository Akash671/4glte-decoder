from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_decode_nas_success():
    payload = {
        "hex_str": "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181",
        "layer": "NAS",
        "channel": "DCCH",
        "direction": "DL",
    }
    resp = client.post("/decode", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["error"] is None
    assert "NAS_Message" in body["result"]


def test_decode_invalid_hex_returns_422():
    payload = {"hex_str": "zz-not-hex", "layer": "NAS", "channel": "DCCH", "direction": "DL"}
    resp = client.post("/decode", json=payload)
    assert resp.status_code == 422  # caught by pydantic validator


def test_decode_bad_channel_rejected_by_schema():
    payload = {"hex_str": "AABB", "layer": "RRC", "channel": "NOT_A_CHANNEL", "direction": "UL"}
    resp = client.post("/decode", json=payload)
    assert resp.status_code == 422  # not a valid Channel enum member


def test_decode_rrc_ok_or_clean_error():
    payload = {"hex_str": "5631F2857DE6", "layer": "RRC", "channel": "DCCH", "direction": "DL"}
    resp = client.post("/decode", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    # Either it decodes, or it fails gracefully with ok=False and an error string
    assert body["ok"] in (True, False)
    if not body["ok"]:
        assert isinstance(body["error"], str)
