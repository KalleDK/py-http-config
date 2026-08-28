import ssl
from pathlib import Path
from unittest.mock import Mock

import pytest

import http_config._ssl as ssl_module
import http_config.config as config_module
from http_config.config import SSLConfig


def test_create_insecure_ssl_context_disables_verification() -> None:
    context = ssl_module.create_insecure_ssl_context()

    assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
    assert context.check_hostname is False
    assert context.verify_mode == ssl.CERT_NONE


def test_create_ssl_context_uses_system_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    create_default_context = Mock()
    monkeypatch.setattr(ssl, "create_default_context", create_default_context)

    result = ssl_module.create_ssl_context(None)

    assert result is create_default_context.return_value
    create_default_context.assert_called_once_with()


def test_create_ssl_context_uses_normalized_ssl_config(monkeypatch: pytest.MonkeyPatch) -> None:
    create_default_context = Mock()
    monkeypatch.setattr(ssl, "create_default_context", create_default_context)
    monkeypatch.setattr(config_module, "CERTIFI_PATH", Path("certifi.pem"))
    ssl_config = SSLConfig.model_validate(
        {
            "capath": Path("certificates"),
            "cadata": "certificate data",
        }
    )

    result = ssl_module.create_ssl_context(ssl_config)

    assert result is create_default_context.return_value
    create_default_context.assert_called_once_with(
        cafile=Path("certifi.pem"),
        capath=Path("certificates"),
        cadata="certificate data",
    )


def test_create_ssl_context_uses_certifi_for_secure_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    create_default_context = Mock()
    certifi_path = Path("certifi.pem")
    monkeypatch.setattr(ssl, "create_default_context", create_default_context)
    monkeypatch.setattr(ssl_module, "CERTIFI_PATH", certifi_path)

    result = ssl_module.create_ssl_context(True)

    assert result is create_default_context.return_value
    create_default_context.assert_called_once_with(cafile=certifi_path)
