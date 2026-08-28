import sys
from datetime import timedelta
from pathlib import Path

import pytest

import http_config.config as config_module
from http_config.config import HTTPConfig, LimitConfig, SSLConfig, TimeoutConfig, load_certifi


def test_ssl_config_create_returns_expected_values() -> None:
    assert SSLConfig.create() is None
    assert SSLConfig.create(insecure=True) is False
    assert SSLConfig.create(insecure=False) is True

    config = SSLConfig.create(cafile=Path("ca.pem"))
    assert isinstance(config, SSLConfig)
    assert config.cafile == Path("ca.pem")


def test_load_certifi_returns_none_when_certifi_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "certifi", None)

    assert load_certifi() is None


def test_ssl_config_cafile_normalized_prefers_explicit_cafile(monkeypatch: pytest.MonkeyPatch) -> None:
    certifi_path = Path("certifi.pem")
    monkeypatch.setattr(config_module, "CERTIFI_PATH", certifi_path)

    config = SSLConfig.model_validate({"cafile": Path("custom-ca.pem")})

    assert config.cafile_normalized == Path("custom-ca.pem")


def test_ssl_config_cafile_normalized_can_ignore_certifi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "CERTIFI_PATH", Path("certifi.pem"))

    config = SSLConfig(ignore_certifi=True)

    assert config.cafile_normalized is None


def test_ssl_config_cafile_normalized_uses_certifi_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    certifi_path = Path("certifi.pem")
    monkeypatch.setattr(config_module, "CERTIFI_PATH", certifi_path)

    assert SSLConfig().cafile_normalized == certifi_path


def test_http_config_accepts_nested_configuration() -> None:
    config = HTTPConfig(
        proxy="https://proxy.example",
        timeout=TimeoutConfig(timeout=timedelta(seconds=5)),
        limits=LimitConfig(max_connections=20),
        ssl=SSLConfig(cafile=Path("ca.pem")),
        log_path=Path("logs"),
    )

    assert config.proxy == "https://proxy.example"
    assert config.timeout.timeout == timedelta(seconds=5)  # type: ignore[union-attr]
    assert config.limits.max_connections == 20  # type: ignore[union-attr]
    assert config.ssl.cafile == Path("ca.pem")  # type: ignore[union-attr]


def test_http_config_accepts_nested_configuration_with_model_validate() -> None:
    config = HTTPConfig(
        proxy="https://proxy.example",
        timeout=TimeoutConfig(timeout=timedelta(seconds=5)),
        limits=LimitConfig(max_connections=20),
        ssl=SSLConfig.model_validate({"cafile": Path("ca.pem")}),
        log_path=Path("logs"),
    )

    assert config.proxy == "https://proxy.example"
    assert config.timeout.timeout == timedelta(seconds=5)  # type: ignore[union-attr]
    assert config.limits.max_connections == 20  # type: ignore[union-attr]
    assert config.ssl.cafile == Path("ca.pem")  # type: ignore[union-attr]
