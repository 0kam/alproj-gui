from __future__ import annotations

import os
from pathlib import Path

from app.core.model_cache import configure_ssl_certificates


def test_configure_ssl_certificates_overrides_invalid_env(monkeypatch: object, tmp_path: Path) -> None:
    invalid_ca = tmp_path / "missing-ca.pem"
    monkeypatch.setenv("SSL_CERT_FILE", str(invalid_ca))
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)

    configured = configure_ssl_certificates()

    assert configured is not None
    assert configured.is_file()
    assert os.environ["SSL_CERT_FILE"] == str(configured)
    assert os.environ["REQUESTS_CA_BUNDLE"] == str(configured)
    assert os.environ["CURL_CA_BUNDLE"] == str(configured)


def test_configure_ssl_certificates_preserves_valid_custom_ca(
    monkeypatch: object, tmp_path: Path
) -> None:
    custom_ca = tmp_path / "custom-ca.pem"
    custom_ca.write_text("dummy")
    monkeypatch.setenv("SSL_CERT_FILE", str(custom_ca))
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)

    configured = configure_ssl_certificates()

    assert configured == custom_ca
    assert os.environ["SSL_CERT_FILE"] == str(custom_ca)
    assert os.environ["REQUESTS_CA_BUNDLE"] == str(custom_ca)
    assert os.environ["CURL_CA_BUNDLE"] == str(custom_ca)
