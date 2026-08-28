import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

import http_config.config as config_module
from http_config._ssl import create_insecure_ssl_context, create_ssl_context
from http_config.config import HTTPConfig, LimitConfig, SSLConfig, TimeoutConfig, load_certifi
from http_config.httpx.client import (
    create_limits,
    create_timeout,
)


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


def test_create_ssl_context_supports_default_custom_and_insecure_modes() -> None:
    default_context = create_ssl_context(None)
    custom_context = create_ssl_context(SSLConfig())
    secure_context = create_ssl_context(True)
    insecure_context = create_ssl_context(False)

    assert default_context.verify_mode.value == 2
    assert custom_context.verify_mode.value == 2
    assert secure_context.verify_mode.value == 2
    assert insecure_context is not default_context
    assert insecure_context.check_hostname is False
    assert insecure_context.verify_mode.value == 0


def test_create_insecure_ssl_context_disables_certificate_verification() -> None:
    context = create_insecure_ssl_context()

    assert context.check_hostname is False
    assert context.verify_mode.value == 0


def test_create_timeout_handles_all_supported_values() -> None:
    assert create_timeout(None) is None
    assert create_timeout(False) == httpx.Timeout(timeout=None)
    assert create_timeout(timedelta(seconds=3)) == httpx.Timeout(timeout=3)
    assert create_timeout(TimeoutConfig()) is None

    timeout = create_timeout(
        TimeoutConfig(
            timeout=timedelta(seconds=1),
            read_timeout=False,
            write_timeout=timedelta(seconds=2),
            connect_timeout=timedelta(seconds=3),
        )
    )

    assert timeout is not None
    assert timeout.connect == 3
    assert timeout.read is None
    assert timeout.write == 2
    assert timeout.pool == 1


def test_create_limits_preserves_configured_values() -> None:
    assert create_limits(None) is None

    limits = create_limits(LimitConfig(max_connections=10, max_keepalive_connections=4))

    assert limits is not None
    assert limits.max_connections == 10
    assert limits.max_keepalive_connections == 4


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
