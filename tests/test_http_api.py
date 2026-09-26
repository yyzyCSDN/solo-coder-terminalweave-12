from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from terminalweave.api.http import Handler


@pytest.fixture
def api_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(address, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload)
    headers = {} if body is None else {"Content-Type": "application/json"}
    connection = HTTPConnection(*address, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_health_endpoint(api_server):
    status, payload = request(api_server, "GET", "/health")
    assert status == 200
    assert payload == {"service": "terminalweave", "status": "ok"}


def test_tide_clearance_endpoint(api_server):
    status, payload = request(
        api_server,
        "POST",
        "/tide/clearance",
        {
            "samples": [
                {"at": "2026-01-01T00:00:00Z", "height_m": 0},
                {"at": "2026-01-01T02:00:00Z", "height_m": 2},
            ],
            "chart_depth_m": 10,
            "draft_m": 9,
            "minimum_clearance_m": 1,
            "at": "2026-01-01T01:00:00Z",
        },
    )
    assert status == 200
    assert payload == {"clearance_m": 2.0, "safe": True}


def test_demurrage_endpoint(api_server):
    status, payload = request(
        api_server,
        "POST",
        "/billing/demurrage",
        {
            "discharge_at": "2026-01-01T00:00:00Z",
            "gate_out_at": "2026-01-03T00:00:00Z",
            "daily_rate": "10",
            "free_days": 0,
            "currency": "USD",
        },
    )
    assert status == 200
    assert payload == {"amount": "20.00", "currency": "USD"}


def test_http_error_contracts(api_server):
    status, payload = request(api_server, "GET", "/missing")
    assert status == 404
    assert payload == {"error": "not_found"}

    connection = HTTPConnection(*api_server, timeout=5)
    try:
        connection.request(
            "POST",
            "/tide/clearance",
            body="{",
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        assert response.status == 400
        assert json.loads(response.read()) == {"error": "invalid_json"}
    finally:
        connection.close()
