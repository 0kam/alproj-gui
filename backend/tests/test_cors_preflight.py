from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    ("origin", "expected_status"),
    [
        ("tauri://localhost", 200),
        ("http://tauri.localhost", 200),
        ("https://tauri.localhost", 200),
        ("http://localhost:1420", 200),
        ("http://localhost:5173", 200),
        ("https://example.com", 400),
    ],
)
def test_health_preflight_cors(origin: str, expected_status: int) -> None:
    client = TestClient(app)

    response = client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.headers.get("access-control-allow-origin") == origin
