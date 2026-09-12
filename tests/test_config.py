from datetime import timedelta
from pathlib import Path

import pytest

from http_config.config import HTTPConfig, LimitConfig, SSLConfig, TimeoutConfig


def test_ssl_config_create_returns_expected_values() -> None:
    assert SSLConfig.create() is None
    assert SSLConfig.create(insecure=True) is False
    assert SSLConfig.create(insecure=False) is True

    config = SSLConfig.create(cafile=Path("ca.pem"))
    assert isinstance(config, SSLConfig)
    assert config.cafile == Path("ca.pem")


def test_ssl_config_cafile_normalized_prefers_explicit_cafile(monkeypatch: pytest.MonkeyPatch) -> None:

    config = SSLConfig.model_validate({"cafile": Path("custom-ca.pem")})

    assert config.cafile_normalized == Path("custom-ca.pem")


def test_timeout_config_accepts_scalar_values() -> None:
    assert TimeoutConfig.model_validate(timedelta(seconds=5)).timeout == timedelta(seconds=5)


def test_http_config_accepts_nested_configuration() -> None:
    config = HTTPConfig(
        proxy="https://proxy.example",
        timeout=TimeoutConfig(timeout=timedelta(seconds=5)),
        limits=LimitConfig(max_connections=20),
        ssl=SSLConfig(cafile=Path("ca.pem")),
        log_path=Path("logs"),
    )

    assert config.proxy == "https://proxy.example"
    assert isinstance(config.timeout, TimeoutConfig)
    assert config.timeout.timeout == timedelta(seconds=5)
    assert isinstance(config.limits, LimitConfig)
    assert config.limits.max_connections == 20
    assert isinstance(config.ssl, SSLConfig)
    assert config.ssl.cafile == Path("ca.pem")


def test_http_config_accepts_nested_configuration_with_model_validate() -> None:
    config = HTTPConfig(
        proxy="https://proxy.example",
        timeout=TimeoutConfig(timeout=timedelta(seconds=5)),
        limits=LimitConfig(max_connections=20),
        ssl=SSLConfig.model_validate({"cafile": Path("ca.pem")}),
        log_path=Path("logs"),
    )

    assert config.proxy == "https://proxy.example"
    assert isinstance(config.timeout, TimeoutConfig)
    assert config.timeout.timeout == timedelta(seconds=5)
    assert isinstance(config.limits, LimitConfig)
    assert config.limits.max_connections == 20
    assert isinstance(config.ssl, SSLConfig)
    assert config.ssl.cafile == Path("ca.pem")


def test_http_config_with_sub_log_path_returns_self_without_log_path() -> None:
    config = HTTPConfig()

    assert config.with_sub_log_path("requests") is config


def test_http_config_with_sub_log_path_appends_path_without_mutating_config() -> None:
    config = HTTPConfig(log_path=Path("logs"))

    updated = config.with_sub_log_path(Path("requests"))

    assert updated is not config
    assert config.log_path == Path("logs")
    assert updated.log_path == Path("logs/requests")
