"""The host's local retirement credential stays narrower than dashboard sign-in."""

from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def maintenance(monkeypatch):
    from hermes_cli import backend_retirement, web_server

    monkeypatch.setattr(web_server, "_SESSION_TOKEN", "private-host-token")
    monkeypatch.setattr(web_server.app.state, "auth_required", True, raising=False)
    monkeypatch.setattr(web_server.app.state, "host_role", "serve", raising=False)
    monkeypatch.setattr(backend_retirement, "retirement", backend_retirement.RetirementFence())
    return web_server, {"X-Hermes-Maintenance-Token": "private-host-token"}


def test_local_operator_can_reserve_and_cancel_retirement_behind_login_gate(maintenance):
    web, headers = maintenance
    client = TestClient(web.app, client=("127.0.0.1", 4000))
    assert client.get("/api/host/identity", headers=headers).json()["role"] == "serve"
    assert client.get("/api/health/idle", headers=headers).json()["idle"] is True
    permit = client.post("/api/health/retirement", headers=headers, json={"action": "prepare"}).json()
    assert permit["ok"] is True
    assert client.post("/api/health/retirement", headers=headers,
                       json={"action": "cancel", "token": permit["token"]}).json() == {"ok": True}


@pytest.mark.parametrize("peer,extra,path", [
    ("192.0.2.4", {}, "/api/health/idle"),
    ("127.0.0.1", {"Origin": "http://localhost"}, "/api/health/idle"),
    ("127.0.0.1", {"Origin": ""}, "/api/health/idle"),
    ("127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}, "/api/health/idle"),
    ("127.0.0.1", {"Forwarded": "for=127.0.0.1"}, "/api/health/idle"),
    ("127.0.0.1", {}, "/api/config"),
    ("127.0.0.1", {"X-Hermes-Maintenance-Token": "wrong"}, "/api/health/idle"),
])
def test_maintenance_token_refuses_remote_browser_proxy_and_other_routes(maintenance, peer, extra, path):
    web, headers = maintenance
    client = TestClient(web.app, client=(peer, 4000))
    assert client.get(path, headers={**headers, **extra}).status_code == 401
